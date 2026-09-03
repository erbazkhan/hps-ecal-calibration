#!/usr/bin/env python

##########################################################################################################################
#
# Adapted from noSVTRecon_swif.py for full pass2 reconstruction
# (PhysicsRun2019_pass2_recon.lcsim) instead of NoSVT/FEE-only recon, with
# two differences:
#   1. Takes an explicit run-list text file (one run number per line) instead
#      of processing every run found under DATA_SOURCE_BASE_DIR.
#   2. RUN_DIR_PREFIX makes the per-run subdirectory naming convention
#      configurable, since /mss/hallb/hps/physrun2019/data/ uses "hps_<run>"
#      rather than the bare zero-padded "<run>" used under evio-skims/fee/.
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
DISK = "50GB"             # Max Disk usage
RAM = "8GB"               # Max RAM usage. Increase if we get OOM-kill error.
TIMELIMIT = "300minutes"  # Max walltime

# SOURCE DATA INFORMATION
DATA_SOURCE_TYPE = "mss"
# DATA_SOURCE_BASE_DIR = "/mss/hallb/hps/physrun2019/data/"
DATA_SOURCE_BASE_DIR = "/mss/hallb/hps/physrun2019/production/evio-skims/fee/"
RUN_DIR_PREFIX = ""

# OUTPUT DATA LOCATION
CACHE_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/custom_gains_full_recon"
MSS_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/custom_gains_full_recon"

# JOB EXECUTION
JAR="/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps-distribution-5.2.2-SNAPSHOT-bin.jar"
STEERING="/org/hps/steering/recon/PhysicsRun2019_pass2_recon.lcsim"
DETECTOR_DIR="/lustre24/expphy/volatile/hallb/hps/ekhan/ws"
DETECTOR="HPS_Physics2019_survey_v4p11_L1L2L3_10615_yaw_0p00317"

CONDITIONS_DB_PATH = "/volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan_scaled_cosmics_only.db" # for new gains
# CONDITIONS_DB_PATH = "/w/hallb-scshelf2102/hps/mgignac/db/hps_conditions_11102025_moller_5.db"  # for existing gains
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

    #Check if the output run folder exists. If not, create it
    for run in RUNS:
        if (not os.path.exists(getCacheOutputDir(run))):
            print("output dir: "+getCacheOutputDir(run)+" does not exists. Create it");
            os.makedirs(getCacheOutputDir(run))
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

            #ADD CHECK ON FILE ALREADY EXISTIN
            fname_check=getCacheOutputDir(RUN)+"/"+FILENAME+".slcio"
            if (os.path.exists(fname_check)):
                print("OUTPUT FILE: "+fname_check+" already exists. skip")
                continue

            fname_check=getMSSOutputDir(RUN)+"/"+FILENAME+".slcio"
            if (os.path.exists(fname_check)):
                print("OUTPUT FILE: "+fname_check+" already exists. skip")
                continue

            OFILENAME=FILENAME
            add_job(WORKFLOW, DATA_SOURCE_BASE_DIR, FILENAME,OFILENAME,RUN, FILENO)


if __name__ == "__main__":
    main(sys.argv[1:])
