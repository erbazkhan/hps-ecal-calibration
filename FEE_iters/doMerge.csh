#!/bin/tcsh -f

source /u/home/holtrop/root/bin/thisroot.csh

if ($#argv < 1) then
    echo "Usage: doMerge.csh <iteration> [Ncores]"
    echo "  iteration: calibration iteration to merge (1, 2, 3, ...)"
    echo "  Ncores: number of parallel hadd jobs (default: 32)"
    exit 1
endif

set iteration=$argv[1]
set Ncores=32
if ($#argv >= 2) set Ncores=$argv[2]

echo "iteration is: $iteration"

if (! -d "outputCache/iteration_$1" ) then
	echo "Folder doesnt exists"
	exit
endif

set folderlist=(`ls outputCache/iteration_$1`)
set N=$#folderlist

echo "Total runs to merge: $N"

# per-run hadd jobs in parallel
set x = 0
while ($x < $N)
    foreach y(`seq 1 1 $Ncores`)
        @ x++
        if ($x > $N) break
        set folder=$folderlist[$x]
        set split = ($folder:as/_/ /)
        @ run = $split[2]
        ( $ROOTSYS/bin/hadd outputCache/$run.$iteration.root outputCache/iteration_$1/$folder/*.root ) &
    end
    wait
end

# final hadd across all runs — must run after all per-run hadds complete
echo "Merging all runs -> outputCache/FEE_iter${iteration}.root"
$ROOTSYS/bin/hadd outputCache/FEE_iter${iteration}.root outputCache/*.$iteration.root
echo "Final merged file: outputCache/FEE_iter${iteration}.root"

echo    "=============== DONE ==============="
