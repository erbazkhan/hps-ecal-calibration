echo 	"Default cores for parallelism: 32"

echo	"=============== RUNNING doReconFlat.csh =============="
echo
./doRecon.csh $1 $2 $3
echo
echo    "=============== MOVING FILES =============="
echo
./doCollectParallel.csh $1 $2
echo
echo    "=============== MERGING =============="
echo
./doMerge.csh $1 $2
echo
echo    "=============== DONE =============="
echo
