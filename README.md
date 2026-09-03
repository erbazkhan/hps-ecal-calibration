# hps-ecal-calibration

Batch/production scripts for reproducing the HPS 2019 ECAL gain calibration
(cosmic + iterative FEE correction).

These scripts drive `hps-java` (`EvioToLcio` / `JobManager`) over 2019 EVIO data,
either through **swif2** workflows or through parallel jobs on interactive nodes,
and merge the resulting ROOT histograms with `hadd`. Gains live in a local SQLite
conditions DB rather than the central HPS DB.

## Pipeline

1. **Cosmic baseline** — `cosmics/doCosmicCalib.csh` runs `CosmicCalibration.lcsim`
   over cosmic runs to produce MIP-signal histogram ROOT files.
2. The merged histogram
   file feeds `HPS-CODE/CALIBRATION/COSMIC/getCosmicGain.C`, which fits the per-crystal
   MIP peaks and computes the baseline ecal gains.
3. **Load gains into a DB** — `util_scripts/insertGainsToDB.csh` inserts the
   baseline gains as an `ecal_gains` collection + `conditions` row in the SQLite DB.
4. **NoSVT reconstruction** — `recon/swifRecon_NoSVT.py` reconstructs the FEE
   skims with `PhysicsRun2019_NoSVT.lcsim` against that DB, writing `.slcio` output
   that feeds the FEE iterations.
5. **FEE gain iterations** — `FEE_iters/` runs `EcalFEECalibration2019.lcsim` over the
   reconstructed `.slcio`, iteration by iteration, comparing the FEE peak to MC to
   correct the gains. Repeat feeding each iteration's output gains back in.
6. **Full reconstruction** — once the final gains (`MeV/ADC`) are uploaded to the DB,
   run a full pass2 reconstruction (`PhysicsRun2019_pass2_recon.lcsim`) with
   `recon/fullRecon_swif.py` (or `recon/fullRecon_and_minidst.py` to also produce
   mini-DSTs). Use this fully reconstructed data to check where the FEE peak E/p
   ratio lands.

## Directories

### `cosmics/`
- `doCosmicCalib.csh <runfile> <tag> [Ncores]` — parallel interactive-node
  reproduction of the COSMIC2019 cosmic-calibration histogram ROOT files.
  Output under `output/<tag>/`.
- `runs.txt` — one run number per line, input to the above.

### `recon/`
swif2 workflows, one job per EVIO file, reconstructing against the local conditions DB.

- `swifRecon_NoSVT.py <workflow>` — NoSVT/FEE-only recon
  (`PhysicsRun2019_NoSVT.lcsim`); processes every run under the source dir.
- `fullRecon_swif.py <workflow> <runlist_file>` — full pass2 recon
  (`PhysicsRun2019_pass2_recon.lcsim`) over an explicit run list;
  `RUN_DIR_PREFIX` sets the per-run subdir naming (`hps_<run>` vs bare `<run>`).
- `fullRecon_and_minidst.py <workflow> <runlist_file>` — same as above, plus a
  chained mini-DST job (`-antecedent`) per file that runs `make_mini_dst` on the
  recon output via `make_minidst_wrapper.sh`.

### `FEE_iters/`
Two ways to run the same FEE-iteration reconstruction:

- **swif2:** `doFeeIter_swif2.py <workflow> <iteration> [runsFile]` — one job per
  `.slcio` file, each running `runFeeIter_job.csh` (per-job worker: stages
  `ecalGains.txt` / `ecalSlopes.txt` / conditions DB into the sandbox, runs the java
  calibration step). Then `swif2 run -workflow <workflow>`.
  Must be run from a dir containing `ecalGains_<iteration-1>.txt` and `ecalSlopes.txt`.
- **Interactive nodes:** `doRecon.csh <iteration> [Ncores] [runsFile]` — same job
  without swif2; fine for a few run periods, use swif2 for large sets (e.g. period 6).
- `runAll.csh <iter> <Ncores> <runsFile>` — `doRecon` → `doCollect` → `doMerge`.
- `doCollect.csh <iteration> [Ncores]` — moves per-job `outputFEEPlots.root` /
  `out.slcio` / logs from `process_<run>_<n>/` into `outputCache/iteration_<iter>/`.
- `doMerge.csh <iteration> [Ncores]` — per-run `hadd`, then a final
  `hadd` → `outputCache/FEE_iter<iteration>.root`.

### `util_scripts/`
- `insertGainsToDB.csh` — insert an `ecal_gains` collection + `conditions` row into
  the SQLite conditions DB from a `channel_id,gain` file.

## Conventions

- **hps-java:** `hps-distribution-5.2.2-SNAPSHOT` jar; detector
  `HPS_Physics2019_survey_v4p11_L1L2L3_10615_yaw_0p00317` resolved from a directory
  on the classpath ahead of the jar.
- **Conditions DB:** local SQLite, pointed at with
  `-Dorg.hps.conditions.url=jdbc:sqlite:...`, staged into each job sandbox as
  `hps_local_conditions.db`.
- **JVM:** always `-Xmx3g -XX:+UseSerialGC` — under a SLURM cgroup RAM fence, an
  implicit heap sizes off total node memory and gets OOM-killed.
- Paths (jar, DB, input/output dirs) are hard-coded at the top of each script — edit
  them for your area on the farm before running.
