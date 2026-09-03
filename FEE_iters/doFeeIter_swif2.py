#!/usr/bin/env python
##########################################################################################################################
# Usage:
# python3 doFeeIter_swif2.py <workflow_name> <iteration_no> [runsFile]
# Afterwards, run the workflow as:
# swif2 run -workflow <workflow_name>
#
# This script is a swif2 version of doReconFlat.csh in the interactive nodes,
# which runs the FEE iteration on a single node with nohup with a few cores.
# It creates a swif2 workflow and adds a job for each input file. Each job
# runs runFeeIter_job.csh, which does the same staging + java call that
# doReconFlat.csh did per-file in its nohup loop.
#
##########################################################################################################################


from optparse import OptionParser
import sys
import os
import re
import glob
import errno
import subprocess

# RESOURCES
NCORES = "1"
DISK = "5GB"
RAM = "4GB"
TIMELIMIT = "240minutes"

INPUT_DIR = "/lustre24/expphy/volatile/hallb/hps/ekhan/recon/pass0.0/fee_ekhan_cosmicV3"
WORKER_SCRIPT = "/volatile/hallb/hps/ekhan/FEE2019/FEE_gains_iterations/p6/runFeeIter_job.csh"
OUTPUT_BASE_DIR = "/volatile/hallb/hps/ekhan/FEE2019/FEE_gains_iterations/p6/out"

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

def find_input_files(runs=None):
    if runs is None:
        return sorted(glob.glob(INPUT_DIR + "/*/*.slcio"))
    files = []
    for run in runs:
        files.extend(sorted(glob.glob(INPUT_DIR + "/" + run + "/*.slcio")))
    return files


def read_runs_file(path):
    runs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                runs.append(line)
    return runs


def run_from_path(path):
    # .../010050/hps_fee_010050.evio.00200-00299.slcio -> "10050"
    m = re.search(r'/(\d+)/[^/]+$', path)
    return str(int(m.group(1)))


def add_job(workflow, index, infile, run, outstub, output_dir, ecal_gains_file, ecal_slopes_file):
    jobname = workflow + "_" + run + "_" + str(index)

    add_command = "swif2 add-job -workflow " + workflow + " -name " + jobname
    # resources
    add_command += " -cores " + NCORES + " -disk " + DISK + " -ram " + RAM + " -time " + TIMELIMIT
    # logs
    add_command += " -stdout " + output_dir + "/log_" + jobname + ".out.txt"
    add_command += " -stderr " + output_dir + "/log_" + jobname + ".err.txt"
    add_command += " -output out.slcio file:" + output_dir + "/" + outstub + ".slcio"
    add_command += " -output outputFEEPlots.root file:" + output_dir + "/" + outstub + ".root"
    # tags
    add_command += " -tag run_number " + run
    add_command += " -tag file_index " + str(index)

    add_command += " " + WORKER_SCRIPT + " " + run + " " + infile + " " + outstub \
                    + " " + ecal_gains_file + " " + ecal_slopes_file

    status = subprocess.call(add_command.split(" "))


def main(argv):
    parser_usage = "doFeeIter_swif2.py workflow iteration [runsFile]"
    parser = OptionParser(usage=parser_usage)
    (options, args) = parser.parse_args(argv)

    if len(args) < 2 or len(args) > 3:
        parser.print_help()
        return

    workflow = args[0]
    iteration = int(args[1])
    gain_idx = iteration - 1

    # optional runsFile: restrict to just these runs, same as doReconFlatRuns.csh;
    # omit it to process every run under INPUT_DIR (original behavior)
    runs = None
    if len(args) == 3:
        runs_file = args[2]
        if not os.path.exists(runs_file):
            print("ERROR: " + runs_file + " does not exist")
            return
        runs = read_runs_file(runs_file)
        print("Runs to be processed:")
        for run in runs:
            print(run)

    # Must be run from the directory containing ecalGains_<gainIdx>.txt and
    # ecalSlopes.txt (matches doReconFlat.csh's own convention of finding
    # these one level up from wherever it ran).
    ecal_gains_file = os.path.abspath("ecalGains_%d.txt" % gain_idx)
    ecal_slopes_file = os.path.abspath("ecalSlopes.txt")
    if not os.path.exists(ecal_gains_file):
        print("ERROR: " + ecal_gains_file + " does not exist")
        return
    if not os.path.exists(ecal_slopes_file):
        print("ERROR: " + ecal_slopes_file + " does not exist")
        return

    output_dir = OUTPUT_BASE_DIR + "/iter" + str(iteration)
    mkdir_p(output_dir)

    # CREATE WORKFLOW
    status = subprocess.call(["swif2", "create", "-workflow", workflow])

    # FIND/ADD JOBS
    files = find_input_files(runs)
    print("Total files to process: " + str(len(files)))

    for index, infile in enumerate(files):
        run = run_from_path(infile)
        outstub = "out_" + run + "_" + str(index)

        # ADD CHECK ON FILE ALREADY EXISTING
        if os.path.exists(output_dir + "/" + outstub + ".slcio"):
            print("Output for run " + run + " index " + str(index) + " already exists. skip")
            continue

        add_job(workflow, index, infile, run, outstub, output_dir, ecal_gains_file, ecal_slopes_file)


if __name__ == "__main__":
    main(sys.argv[1:])
