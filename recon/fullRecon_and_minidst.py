#!/usr/bin/env python

##########################################################################################################################
#
# Adapted from noSVTRecon_swif.py for full pass2 reconstruction
# (PhysicsRun2019_pass2_recon.lcsim) instead of NoSVT/FEE-only recon, with
# these differences:
#   1. Takes an explicit run-list text file (one run number per line) instead
#      of processing every run found under DATA_SOURCE_BASE_DIR.
#   2. RUN_DIR_PREFIX makes the per-run subdirectory naming convention
#      configurable, since /mss/hallb/hps/physrun2019/data/ uses "hps_<run>"
#      rather than the bare zero-padded "<run>" used under evio-skims/fee/.
#   3. Each recon job gets a second, chained job (add_minidst_job(), linked
#      via -antecedent) that runs make_mini_dst on that job's own slcio
#      output as soon as it succeeds -- see make_minidst_wrapper.sh, needed
#      because make_mini_dst is exposed by sourcing HPS/ROOT setup scripts,
#      not a standalone binary swif2's job exec would find on its own. If
#      a file's recon output already exists (e.g. from an earlier workflow),
#      the minidst job is submitted directly with no antecedent instead.
#
##########################################################################################################################

from optparse import OptionParser
import os.path
import sys
import re
import subprocess
import glob
import errno
import os
from pathlib import Path


#################################################### GLOBAL VARIABLES ####################################################

# DEBUG
VERBOSE = False

# RESOURCES
NCORES = "1"              # Number of CPU cores
DISK = "16GB"             # Max Disk usage
RAM = "12GB"               # Max RAM usage. Increase if we get OOM-kill error.
TIMELIMIT = "2400minutes"  # Max walltime

# SOURCE DATA INFORMATION
DATA_SOURCE_TYPE = "mss"
# DATA_SOURCE_BASE_DIR = "/mss/hallb/hps/physrun2019/data/"
DATA_SOURCE_BASE_DIR = "/mss/hallb/hps/physrun2019/production/evio-skims/fee"
RUN_DIR_PREFIX = "" # "hps_"

# OUTPUT DATA LOCATION
CACHE_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/custom_gains_full_recon/slcio"     #******
MSS_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/custom_gains_full_recon/slcio"       #******
MINIDST_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/custom_gains_full_recon/minidst" #******
MINIDST_WRAPPER = "/volatile/hallb/hps/ekhan/recon/make_minidst_wrapper.sh"

# MINIDST RESOURCES
MINIDST_NCORES = "1"
MINIDST_DISK = "16GB"
MINIDST_RAM = "8GB"
MINIDST_TIMELIMIT = "2400minutes"

# JOB EXECUTION
JAR="/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps-distribution-5.2.2-SNAPSHOT-bin.jar"
STEERING="/org/hps/steering/recon/PhysicsRun2019_pass2_recon.lcsim"
DETECTOR_DIR="/lustre24/expphy/volatile/hallb/hps/ekhan/ws"
DETECTOR="HPS_Physics2019_survey_v4p11_L1L2L3_10615_yaw_0p00317"

CONDITIONS_DB_PATH = "/volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan_scaled_cosmics_only.db"   # for new gains
# CONDITIONS_DB_PATH = "/w/hallb-scshelf2102/hps/mgignac/db/hps_conditions_11102025_moller_5.db"  # for regular gains

CONDITIONS_DB_URL = "jdbc:sqlite:"+CONDITIONS_DB_PATH
TMPDIR = "/lustre24/expphy/volatile/hallb/hps/ekhan/tmp"

#MKDIR DIR WITH PARENT
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def getCacheOutputDir(run):
    ret=CACHE_OUTPUT_DIR+"/"+str(run).zfill(6)
    return ret

def getMSSOutputDir(run):
    ret=MSS_OUTPUT_DIR+"/"+str(run).zfill(6)
    return ret

def getMinidstOutputDir(run):
    ret=MINIDST_OUTPUT_DIR+"/"+str(run).zfill(6)
    return ret

def getRunDir(base_dir, run):
    return base_dir+"/"+RUN_DIR_PREFIX+str(run).zfill(6)

####################################################### FIND FILES #######################################################

def find_files(DATA_SOURCE_DIR,RUN):
    # CHANGE TO THE DIRECTORY CONTAINING THE INPUT FILES
    current_dir = os.getcwd()
    data_dir=getRunDir(DATA_SOURCE_DIR, RUN)
    os.chdir(data_dir)


    # SEARCH FOR THE FILES
    file_signature = "*.evio.*"
    file_list = glob.glob(file_signature)

    # CHANGE BACK TO THE PREVIOUS DIRECTORY
    os.chdir(current_dir)
    return file_list


######################################################## ADD JOB #########################################################

def add_job(WORKFLOW, DATA_SOURCE_DIR, INFILENAME, OUTFILENAME, RUNNO, FILENO):

    # PREPARE NAMES
    DATA_OUTPUT_DIR = getCacheOutputDir(RUNNO)
    DATASOURCE_DIR=getRunDir(DATA_SOURCE_BASE_DIR, RUNNO)

    RUNNO=str(RUNNO)
    FILENO=str(FILENO)
    STUBNAME = RUNNO + "_" + FILENO
    JOBNAME = WORKFLOW + "_" + STUBNAME

    # NOTE: -D<name>=<value> here (JVM system properties) MUST come before -cp.
    # These are different from EvioToLcio's own "-D name=value" steering-file
    # variable option that appears later in the command.
    command = "java -Xmx3g -XX:+UseSerialGC -Djava.io.tmpdir="+TMPDIR+" -Dorg.hps.conditions.url="+CONDITIONS_DB_URL+" -cp "+DETECTOR_DIR+":"+JAR+" org.hps.evio.EvioToLcio"+" -r -x "+STEERING+" -d "+DETECTOR+" -R "+RUNNO+" -DoutputFile="+OUTFILENAME+" infile0 "



    # CREATE ADD-JOB COMMAND (swif2 syntax)
    # job
    add_command = "swif2 add-job -workflow " + WORKFLOW + " -name " + JOBNAME
    # resources
    add_command += " -cores " + NCORES + " -disk " + DISK + " -ram " + RAM + " -time " + TIMELIMIT
    # logs -- explicit, so we're never stuck guessing where output landed
    add_command += " -stdout " + DATA_OUTPUT_DIR + "/log_" + OUTFILENAME + ".out.txt"
    add_command += " -stderr " + DATA_OUTPUT_DIR + "/log_" + OUTFILENAME + ".err.txt"
    # inputs
    add_command += " -input infile0 "+ DATA_SOURCE_TYPE + ":" + DATASOURCE_DIR + "/" + INFILENAME
    # second input: stage our own conditions DB into the job's sandbox under
    # the exact name it was seen looking for -- see CONDITIONS_DB_PATH comment
    add_command += " -input hps_local_conditions.db file:" + CONDITIONS_DB_PATH
    #output
    add_command += " -output "+OUTFILENAME+".slcio"+" file:"+DATA_OUTPUT_DIR+"/"+OUTFILENAME+".slcio"
    # tag
    add_command += " -tag run_number " + RUNNO
    # tags
    add_command += " -tag file_number " + FILENO
    # command
    add_command += " " + command

    # ADD JOB
    status = subprocess.call(add_command.split(" "))

    return JOBNAME


################################################### ADD MINIDST JOB ######################################################

def add_minidst_job(WORKFLOW, RECON_JOBNAME, RECON_OUTPUT_DIR, OUTFILENAME, RUNNO, FILENO):
    # Chained to RECON_JOBNAME via -antecedent when a fresh recon job was
    # just submitted in this same pass -- this job then only becomes
    # eligible once that recon job succeeds. RECON_JOBNAME is None when the
    # recon .slcio already existed going in (e.g. recon already completed
    # in an earlier workflow) -- there's nothing to chain to in that case,
    # the input's already sitting there ready to stage.

    RUNNO=str(RUNNO)
    FILENO=str(FILENO)
    JOBNAME = WORKFLOW + "_" + RUNNO + "_" + FILENO + "_minidst"

    MINIDST_OUT_DIR = getMinidstOutputDir(RUNNO)
    SLCIO_NAME = OUTFILENAME + ".slcio"
    # matches make_minidst_wrapper.sh's underlying bash script convention:
    # $(basename ${f%.slcio})_minidst.root
    ROOT_NAME = OUTFILENAME + "_minidst.root"

    command = "bash "+MINIDST_WRAPPER+" "+SLCIO_NAME+" "+ROOT_NAME

    add_command = "swif2 add-job -workflow " + WORKFLOW + " -name " + JOBNAME
    if RECON_JOBNAME is not None:
        add_command += " -antecedent " + RECON_JOBNAME
    add_command += " -cores " + MINIDST_NCORES + " -disk " + MINIDST_DISK + " -ram " + MINIDST_RAM + " -time " + MINIDST_TIMELIMIT
    add_command += " -stdout " + MINIDST_OUT_DIR + "/log_" + ROOT_NAME + ".out.txt"
    add_command += " -stderr " + MINIDST_OUT_DIR + "/log_" + ROOT_NAME + ".err.txt"
    # input: stage the recon job's own output slcio back in, from the
    # persistent location the recon job's own -output already copied it to
    add_command += " -input " + SLCIO_NAME + " file:" + RECON_OUTPUT_DIR + "/" + SLCIO_NAME
    add_command += " -output " + ROOT_NAME + " file:" + MINIDST_OUT_DIR + "/" + ROOT_NAME
    add_command += " -tag run_number " + RUNNO
    add_command += " -tag file_number " + FILENO
    add_command += " " + command

    status = subprocess.call(add_command.split(" "))


########################################################## MAIN ##########################################################

def main(argv):
    parser_usage = "swifFullReconRunlist_ekhan.py workflow runlist_file"
    parser = OptionParser(usage=parser_usage)
    (options, args) = parser.parse_args(argv)

    if (len(args) != 2):
        parser.print_help()
        return

    # GET ARGUMENTS
    WORKFLOW = args[0]
    RUNFILE = args[1]

    # Make sure our custom tmpdir exists before any job can reference it
    mkdir_p(TMPDIR)

    # Get list of runs from the runlist file (one run number per line,
    # same convention as COSMIC2019/data/swif.py's fileWithRuns argument)
    RUNS=[]
    if (os.path.exists(RUNFILE)):
        fff=open(RUNFILE,"r")
        for line in fff:
            line=line.strip()
            if (len(line)==0 or line.startswith("#")):
                continue
            RUNS.append(int(line))
        fff.close()
    else:
        print("runlist file "+RUNFILE+" does not exist. exit")
        exit(1)
    print("Runs to process: ",RUNS)

    # Check if the output run folder exists. If not, create it
    for run in RUNS:
        if (not os.path.exists(getCacheOutputDir(run))):
            print("output dir: "+getCacheOutputDir(run)+" does not exists. Create it");
            os.makedirs(getCacheOutputDir(run))
            print("DONE")
        if (not os.path.exists(getMinidstOutputDir(run))):
            print("minidst output dir: "+getMinidstOutputDir(run)+" does not exists. Create it");
            os.makedirs(getMinidstOutputDir(run))
            print("DONE")

    # CREATE WORKFLOW
    status = subprocess.call(["swif2", "create", "-workflow", WORKFLOW])


    # FIND/ADD JOBS
    for RUN in RUNS:
        print("Doing RUN: ",RUN)
        # Find files for run number
        file_list = ""
        run_dir = getRunDir(DATA_SOURCE_BASE_DIR, RUN)
        if (os.path.exists(run_dir)):
            file_list = find_files(DATA_SOURCE_BASE_DIR,RUN)
        else:
            print("run dir "+run_dir+" does not exist, skipping run "+str(RUN))
            continue

        if (len(file_list) == 0):
            print("file_list for run: ",RUN,"is empty")
            continue

        print(file_list)


        # Add jobs to workflow. Run-number sanity check just confirms the
        # known run number appears in the filename, rather than assuming a
        # fixed underscore-delimited position -- naming differs between
        # "hps_fee_<run>.evio.*" (evio-skims) and "hps_<run>.evio.*" (raw data).
        ii=0
        for FILENAME in file_list:
            if (str(RUN).zfill(6) not in FILENAME) and (str(RUN) not in FILENAME):
                print("ERROR: run number ",RUN," not found in filename: ",FILENAME)
                exit(1)
            FILENO=ii
            ii=ii+1
            OFILENAME=FILENAME

            # If the minidst .root already exists, there's nothing left to
            # do for this file at all -- skip both stages.
            minidst_check=getMinidstOutputDir(RUN)+"/"+OFILENAME+"_minidst.root"
            if (os.path.exists(minidst_check)):
                print("MINIDST FILE: "+minidst_check+" already exists. skip")
                continue

            # Does the recon .slcio already exist (e.g. from an earlier
            # workflow)? If so, there's no fresh recon job to chain a
            # -antecedent to -- submit the minidst job directly against the
            # existing file. Otherwise submit recon first, then chain
            # minidst to the recon job we just added.
            recon_check=getCacheOutputDir(RUN)+"/"+OFILENAME+".slcio"
            recon_check_mss=getMSSOutputDir(RUN)+"/"+OFILENAME+".slcio"
            if (os.path.exists(recon_check) or os.path.exists(recon_check_mss)):
                print("RECON FILE: "+recon_check+" already exists, submitting minidst only")
                add_minidst_job(WORKFLOW, None, getCacheOutputDir(RUN), OFILENAME, RUN, FILENO)
            else:
                recon_jobname = add_job(WORKFLOW, DATA_SOURCE_BASE_DIR, FILENAME,OFILENAME,RUN, FILENO)
                add_minidst_job(WORKFLOW, recon_jobname, getCacheOutputDir(RUN), OFILENAME, RUN, FILENO)


if __name__ == "__main__":
    main(sys.argv[1:])
