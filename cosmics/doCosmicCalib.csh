#!/bin/tcsh -f
#
# Author: Erbaz Khan (July 2026)
#
# Parallel, interactive-node reproduction of the COSMIC2019 cosmic-calibration
# histogram ROOT files,
#
# Usage: doCosmicCalib.csh <runfile> <tag> [Ncores]
#   runfile : text file, one run number per line (e.g. runs.txt)
#   tag     : label for this reproduction attempt (output goes to output/<tag>/)
#   Ncores  : number of parallel java jobs per batch (default: 32)

if ($#argv < 2) then
    echo "Usage: doCosmicCalib.csh <runfile> <tag> [Ncores]"
    echo "  runfile: text file with one run number per line (e.g. runs.txt)"
    echo "  tag: label for this reproduction attempt, used in the output path"
    echo "  Ncores: number of parallel java jobs (default: 32)"
    exit 1
endif

set runfile=$argv[1]
set tag=$argv[2]
set Ncores=32
if ($#argv >= 3) set Ncores=$argv[3]

# --- VERIFY/EDIT THESE THREE LINES ON THE FARM ---
source /u/home/holtrop/root/bin/thisroot.csh # Dont need it you have your own ROOT setup
set jar=/lustre24/expphy/volatile/hallb/hps/ekhan/COSMIC2019/data/hps-distribution-4.5-SNAPSHOT-bin.jar
set inputDir=/cache/hallb/hps/physrun2019/data
# --------------------------------------------------
set class=org.hps.evio.EvioToLcio
set steering=/org/hps/steering/analysis/CosmicCalibration.lcsim
set detector=HPS-PhysicsRun2019-v1-4pt5
set outputDir=output/$tag

if (! -f "$runfile") then
    echo "runfile $runfile not found"
    exit 1
endif

mkdir -p $outputDir

set nonomatch

set filelist = ( )
set N = 0
foreach run(`cat $runfile`)
    # zero-padded stub, e.g. run 9179 -> "hpsecal_009179"; matches swif.py's
    # own file_signature = "hpsecal_"+run.zfill(6)+"*evio*" for BOTH cases --
    # there's no extra wildcard segment before the run number.
    set runpadded = `printf "hpsecal_%06d" $run`
    if ($run >= 10000) then
        set pattern = "$inputDir/$runpadded/${runpadded}*evio*"
    else
        set pattern = "$inputDir/${runpadded}*evio*"
    endif
    set files = ( $pattern )
    if ("$files[1]" == "$pattern" && ! -e "$files[1]") then
        echo "WARNING: no files found for run $run -- tried pattern: $pattern"
        echo "         (run this by hand on the farm: ls $pattern)"
        continue
    endif
    foreach f($files)
        set outbase = `basename $f`
        set outfile = $outputDir/$runpadded/${outbase}.root
        if (-f $outfile) then
            echo "Skipping $f (output already exists: $outfile)"
            continue
        endif
        @ N++
        set filelist = ($filelist $f)
    end
end

echo "Total files to process: $N"

set x = 0
while ($x < $N)
    echo "Start batch"
    foreach y(`seq 1 1 $Ncores`)
        @ x++
        if ($x > $N) break

        set f = $filelist[$x]
        set outbase = `basename $f`

        # extract run number from filename: hpsecal_009179.evio.00003 -> 9179
        # (mirrors swif.py: STRING_RUN=FILENAME.split(".")[0]; run=int(STRING_RUN.split("_")[1]))
        set string_run = `echo $outbase | cut -d. -f1`
        set run = `echo $string_run | cut -d_ -f2 | sed 's/^0*//'`
        # recompute runpadded HERE, per file -- the file-listing loop above
        # only sets it per RUN, and by this point it's stale (left over from
        # whichever run was last in that loop), not the run this file belongs to
        set runpadded = `printf "hpsecal_%06d" $run`

        echo "  x=$x run=$run file=$f"
        mkdir -p $outputDir/$runpadded
        set out = $outputDir/$runpadded/${outbase}

        nohup java -cp $jar $class -r -x $steering -d $detector -R 10022 \
              -DoutputFile=$out $f >& ${out}.log &
    end
    wait
    echo "Stop batch"
    echo
end

echo "Done. Per-file outputs are in $outputDir/<runpadded>/*.root"
echo

# --- Merge per-file outputs into per-run files ---
echo "Merging per-file outputs into per-run files..."
foreach run(`cat $runfile`)
    set runpadded = `printf "hpsecal_%06d" $run`
    if (-d "$outputDir/$runpadded") then
        $ROOTSYS/bin/hadd -f $outputDir/$run.$tag.root $outputDir/$runpadded/*.root
    else
        echo "  skipping run $run -- no output directory $outputDir/$runpadded"
    endif
end
echo "Done merging. Per-run merged files: $outputDir/<run>.$tag.root"
echo "(needs \$ROOTSYS set in your environment -- source your farm's ROOT setup first if this fails)"

# --- Combine all per-run merged files into one per-tag file, matching the
#     COSMIC2019/data/output/combined/combined.<tag>.root convention used
#     for the original production files ---
set perRunFiles = ( $outputDir/*.$tag.root )
if ("$perRunFiles[1]" == "$outputDir/*.$tag.root" && ! -e "$perRunFiles[1]") then
    echo "No per-run merged files found in $outputDir -- skipping combined hadd"
else
    echo "Combining all per-run files into one per-tag file..."
    mkdir -p $outputDir/combined
    $ROOTSYS/bin/hadd -f $outputDir/combined/combined.$tag.root $perRunFiles
    echo "Done. Combined file: $outputDir/combined/combined.$tag.root"
    echo "This file goes as input into the HPS-CODE/CALIBRATION/COSMIC/getCosmicGain.C macro to produce cosmic gains (MeV/ADC)."
endif
