#!/bin/tcsh -f

if ($#argv < 1) then
    echo "Usage: doCollect.csh <iteration> [Ncores]"
    echo "  iteration: calibration iteration to merge (1, 2, 3, ...)"
    echo "  Ncores: number of parallel hadd jobs (default: 32)"
    exit 1
endif

set iter=$argv[1]
set Ncores=32
if ($#argv >= 2) set Ncores=$argv[2]

if (! -d outputCache) mkdir outputCache
if (! -d outputCache/iteration_${iter}) mkdir outputCache/iteration_${iter}

set dirlist=(`ls -d process_*_*/`)
set N=$#dirlist

echo "Total process dirs: $N"

set x = 0
while ($x < $N)
    foreach y(`seq 1 1 $Ncores`)
        @ x++
        if ($x > $N) break

        set procdir=$dirlist[$x]
        set dirname=`basename $procdir`
        set parts=($dirname:as/_/ /)   # process_10105_3 → (process 10105 3)
        set run=$parts[2]

        set runPadded=`printf "%06d" $run`
        set outdir=outputCache/iteration_${iter}/hps_${runPadded}

        mkdir -p $outdir

        if (-f ${procdir}/outputFEEPlots.root) then
            ( mv ${procdir}/outputFEEPlots.root ${outdir}/${dirname}.root ; \
              mv ${procdir}/out.slcio            ${outdir}/${dirname}.slcio ; \
              mv ${procdir}/log.txt              ${outdir}/${dirname}.log ) &
        else
            echo "WARNING: no outputFEEPlots.root in ${procdir}, skipping"
        endif
    end
    wait
end

echo "Collection complete -> outputCache/iteration_${iter}/"

