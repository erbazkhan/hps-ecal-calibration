#!/bin/tcsh -f
#############################################################################################
#
# This script runs the FEE-iteration reconstruction for 2019 data in the
# interactive nodes of the farm, in a manner similar to doFeeIter_swif2.py, but without swif2.
# It works well if we dont run it for too many runs at once like period 1 through 5.
# but for a large number of runs, as in period 6, swif2 is better.
#
############################################################################################

if ($#argv < 1) then
    echo "Usage: doRecon.csh <iteration> [Ncores] [runsFile]"
    echo "  iteration: calibration iteration to merge (1, 2, 3, ...)"
    echo "  Ncores: number of parallel hadd jobs (default: 32)"
    echo "  runsFile: optional file listing run numbers (one per line) to"
    echo "            restrict to; if omitted, processes every run under inputDir"
    exit 1
endif

set iter=$argv[1]
@ gainIdx = $iter - 1
set Ncores=32
if ($#argv >= 2) set Ncores=$argv[2]
set runsFile=""
if ($#argv >= 3) set runsFile=$argv[3]

set jar=/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps-distribution-5.2.2-SNAPSHOT-bin.jar
set steering=/org/hps/steering/calibration/EcalFEECalibration2019.lcsim
set detectorDir = /lustre24/expphy/volatile/hallb/hps/ekhan/ws
set detector     = HPS_Physics2019_survey_v4p11_L1L2L3_10615_yaw_0p00317
set inputDir=/lustre24/expphy/volatile/hallb/hps/ekhan/recon/pass0.0/fee_ekhan_cosmicV3
set TMPDIR = /lustre24/expphy/volatile/hallb/hps/ekhan/tmp
set CONDITIONS_DB_PATH = /volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan_scaled_cosmics.db
mkdir -p $TMPDIR

# build a flat list of slcio files -- either every run under $inputDir (no
# runsFile given, same as doReconFlat.csh), or only runs listed in runsFile --
# skipping runs that already have process dirs
set nonomatch
set list=( )
set N=0

if ("$runsFile" != "") then
    echo "Runs to be processed:"
    cat $runsFile
    echo ''

    if (! -e $runsFile) then
        echo "ERROR: $runsFile does not exist"
        exit 1
    endif
    foreach run(`cat $runsFile`)
        # set rundir = `printf "%05d" $run`
        set rundir = $run
        foreach file($inputDir/$rundir/*.slcio)
            if (! -e $file) then
                echo "No slcio files found for run $run under $inputDir/$rundir"
                continue
            endif
            set existing=`find . -maxdepth 1 -name "process_${run}_*" -type d | wc -l`
            if ($existing > 0) then
                echo "Skipping run $run (process_${run}_* exists)"
                continue
            endif
            @ N = $N + 1
            set list = ($list $file)
        end
    end
else
    foreach file($inputDir/*/*.slcio)
        set rundirname=`echo $file | sed 's|.*/\([0-9][0-9]*\)/[^/]*$|\1|'`
        set run=`echo $rundirname | sed 's/^0*//'`
        set existing=`find . -maxdepth 1 -name "process_${run}_*" -type d | wc -l`
        if ($existing > 0) then
            echo "Skipping run $run (process_${run}_* exists)"
            continue
        endif
        @ N = $N + 1
        set list = ($list $file)
    end
endif

echo "Total files to process: $N"

set x = 0
while ($x < $N)
    echo "Start batch"
    foreach y(`seq 1 1 $Ncores`)
        @ x++
        if ($x > $N) break

        set file=$list[$x]

        # extract run number from path: fee/010105/file.slcio -> 10105
        set rundirname=`echo $file | sed 's|.*/\([0-9][0-9]*\)/[^/]*$|\1|'`
        set run=`echo $rundirname | sed 's/^0*//'`

        echo "  x=$x run=$run $file"
        rm -rf process_${run}_$x
        mkdir process_${run}_$x
        cd process_${run}_$x
        cp ../ecalGains_${gainIdx}.txt ecalGains.txt
        cp ../ecalSlopes.txt .
        # -Dorg.hps.conditions.url alone wasn't honored (still opened/created an
        # empty ./hps_local_conditions.db -- see swifSQLITE_ekhan.py's comment,
        # same node-dependent behavior seen there). Stage the real DB under the
        # exact relative name it's actually looking for as a second, redundant fix.
        # Symlink, not copy -- DB is 500MB+ and this is read-only lookup traffic
        # (SELECT ... WHERE run_start <= ... AND run_end >= ...), so concurrent
        # jobs sharing the same underlying file is fine.
        ln -s $CONDITIONS_DB_PATH hps_local_conditions.db
        nohup java -Djava.io.tmpdir=$TMPDIR -Dorg.hps.conditions.url=jdbc:sqlite:$CONDITIONS_DB_PATH -cp ${detectorDir}:${jar} org.hps.job.JobManager -r -d $detector -R $run -i $file -DoutputFile=out $steering >& log.txt &
        cd ..
    end
    wait
    echo "Stop batch\n"
end
