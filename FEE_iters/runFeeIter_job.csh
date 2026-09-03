#!/bin/tcsh -f
# Per-job worker for the FEE-iteration swif2 workflow (doFeeIter_swif2.py).
# Runs inside swif2's own per-job sandbox working directory -- does the same
#
# Args: <run> <infile> <outstub> <ecalGainsFile> <ecalSlopesFile>

if ($#argv != 5) then
    echo "Usage: runFeeIter_job.csh <run> <infile> <outstub> <ecalGainsFile> <ecalSlopesFile>"
    exit 1
endif

set run             = $argv[1]
set infile          = $argv[2]
set outstub         = $argv[3]
set ecalGainsFile   = $argv[4]
set ecalSlopesFile  = $argv[5]

set jar=/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps-distribution-5.2.2-SNAPSHOT-bin.jar
set steering=/org/hps/steering/calibration/EcalFEECalibration2019.lcsim
set detectorDir=/lustre24/expphy/volatile/hallb/hps/ekhan/ws
set detector=HPS_Physics2019_survey_v4p11_L1L2L3_10615_yaw_0p00317
set TMPDIR=/lustre24/expphy/volatile/hallb/hps/ekhan/tmp
set CONDITIONS_DB_PATH=/volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan_scaled_cosmics.db

mkdir -p $TMPDIR

# Steering file reads these two by their bare relative name (<gainFile>ecalGains.txt</gainFile>,
# <slopeFile>ecalSlopes.txt</slopeFile>), so they must land under those exact names in cwd.
cp $ecalGainsFile ecalGains.txt
cp $ecalSlopesFile ecalSlopes.txt

# Symlink, not copy -- DB is 500MB+, this is read-only lookup traffic, and every
# concurrent swif2 job doing this is fine sharing the same underlying file.
ln -s $CONDITIONS_DB_PATH hps_local_conditions.db

# -Xmx3g / RAM=4GB in doFeeIter_swif2.py: same OOM lesson as swifSQLITE_ekhan.py --
# under a SLURM-cgroup RAM fence, no explicit -Xmx risks the JVM sizing its default
# heap off the node's total memory instead of what was actually fenced off.
# -DoutputFile=out is deliberately fixed, not $outstub: FEEClusterPlotter.java
# hardcodes aida.saveAs("outputFEEPlots.root") regardless of ${outputFile}, so
# giving each job a "unique" outputFile name was never going to make the .root
# output unique -- it's always outputFEEPlots.root, full stop. LCIOWriter's
# ${outputFile}.slcio substitution is genuine, but swif2's reap step appears to
# fail the whole job (not copying either declared output) if even one expected
# output file is missing -- so both must be declared under their real, fixed
# in-sandbox names (out.slcio / outputFEEPlots.root); $outstub is only used by
# doFeeIter_swif2.py to build a unique *destination* path for each.
java -Xmx3g -XX:+UseSerialGC \
     -Djava.io.tmpdir=$TMPDIR -Dorg.hps.conditions.url=jdbc:sqlite:hps_local_conditions.db \
     -cp ${detectorDir}:${jar} org.hps.job.JobManager \
     -r -d $detector -R $run -i $infile -DoutputFile=out $steering
