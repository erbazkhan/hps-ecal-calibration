#!/usr/bin/env python

"""
Script: noSVTRecon_swif.py
Description:
    Generates and submits workflow batch jobs iFarm for HPS 2019 dataset reconstruction without
    SVT tracking (PhysicsRun2019_NoSVT.lcsim).
    Points to a local SQLite conditions database to reconstruct with consmic gains. Run this 
    once you have baseline cosmic gains uploaded to a local DB to reconstruct the raw data.
    This data can be used to perform FEE gain iterations to do corrections on the baseline gains.
    The output files are saved to the volatile directory in slcio format.

Usage:
    python noSVTRecon_swif.py [options]

Example:
    python noSVTRecon_swif.py -r 10615 -w hps_noSVT_recon_pass0
    python noSVTRecon_swif.py --help
"""

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
NCORES = "1"  # Number of CPU cores
DISK = "30GB"  # Max Disk usage
RAM = "4GB"  # Max RAM usage
TIMELIMIT = "240minutes"  # Max walltime

# SOURCE DATA INFORMATION
DATA_SOURCE_TYPE = "mss"
DATA_SOURCE_BASE_DIR = "/mss/hallb/hps/physrun2019/production/evio-skims/fee/"

# OUTPUT DATA LOCATION
CACHE_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/pass0.0/fee_ekhan_cosmicV1"
MSS_OUTPUT_DIR = "/volatile/hallb/hps/ekhan/recon/pass0.0/fee_ekhan_cosmicV1"

# JOB EXECUTION
JAR="/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps-distribution-5.2.2-SNAPSHOT-bin.jar"
STEERING="/org/hps/steering/recon/PhysicsRun2019_NoSVT.lcsim"
DETECTOR_DIR="/lustre24/expphy/volatile/hallb/hps/ekhan/ws"
DETECTOR="HPS_Physics2019_survey_v4p11_L1L2L3_10615_yaw_0p00317"
CONDITIONS_DB_PATH = "/volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan_scaled_cosmics.db"
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

####################################################### FIND FILES #######################################################

def find_files(DATA_SOURCE_DIR,RUN):
    # CHANGE TO THE DIRECTORY CONTAINING THE INPUT FILES
    current_dir = os.getcwd()
    data_dir=DATA_SOURCE_DIR+"/"+str(RUN).zfill(6)
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
    DATASOURCE_DIR=DATA_SOURCE_BASE_DIR+"/"+str(RUNNO).zfill(6)

    RUNNO=str(RUNNO)
    FILENO=str(FILENO)
    STUBNAME = RUNNO + "_" + FILENO
    JOBNAME = WORKFLOW + "_" + STUBNAME

    # NOTE: -D<name>=<value> here (JVM system properties) MUST come before -cp.
    # These are different from EvioToLcio's own "-D name=value" steering-file
    # variable option that appears later in the command.
    # -Xmx3g -XX:+UseSerialGC: matches doRecon.csh's proven-working settings.
    # Without an explicit -Xmx, the JVM sizes its default heap off the node's
    # total memory rather than what SLURM actually fenced off for us via
    # -ram, and gets OOM-killed once it grows past that fence.
    # DETECTOR_DIR on the classpath ahead of JAR: org.lcsim resolves detector
    # names as classpath resources, so a plain directory containing a
    # DETECTOR-named subdirectory works the same as one bundled in the jar.
    command = "java -Xmx3g -XX:+UseSerialGC -Djava.io.tmpdir="+TMPDIR+" -Dorg.hps.conditions.url="+CONDITIONS_DB_URL+" -cp "+DETECTOR_DIR+":"+JAR+" org.hps.evio.EvioToLcio"+" -r -x "+STEERING+" -d "+DETECTOR+" -R "+RUNNO+" -DoutputFile="+OUTFILENAME+" infile0 "



    # CREATE ADD-JOB COMMAND (swif2 syntax -- no -project/-track/-os, those
    # were old swif v1 flags with no swif2 equivalent)
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
    parser_usage = "swifSQLITE_ekhan.py workflow"
    parser = OptionParser(usage=parser_usage)
    (options, args) = parser.parse_args(argv)

    if (len(args) != 1):
        parser.print_help()
        return

    # GET ARGUMENTS
    WORKFLOW = args[0]

    # Make sure our custom tmpdir exists before any job can reference it
    mkdir_p(TMPDIR)

    #Get list of runs
    RUNS=[]
    dirs=os.listdir(DATA_SOURCE_BASE_DIR)
    for directory in dirs:
        if ("hps" in directory):
            continue
        run=int(directory)
        RUNS.append(run)
    #Check if the run folder exists. If not, create again
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
        if (os.path.exists(DATA_SOURCE_BASE_DIR)):
            file_list = find_files(DATA_SOURCE_BASE_DIR,RUN)
        else:
            continue

        if (len(file_list) == 0):
            print("file_list for run: ",RUN,"is empty")
            continue

        print(file_list)


	#Strip file name. Format:
	# hps_fee_run.evio.FILEMIN-FILEMAX
	# Add jobs to workflow
        ii=0
        for FILENAME in file_list:
            STRING_RUN=FILENAME.split(".")[0]
            runFromFile = int(STRING_RUN.split("_")[2])
            FILENO=ii
            ii=ii+1
            if (runFromFile != RUN):
                print("ERROR, runFromFile: ",runFromFile,"different from RUN: ",RUN)
                exit(1)


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
