#!/bin/tcsh -f
#
# Stage EVIO files
# `jcache get` takes no destination argument -- it automatically mirrors
# each /mss/... path under /cache/... . This call is ASYNCHRONOUS: it
# submits a tape-retrieval request and returns immediately. It does NOT
# block until the files are actually staged. To know when it's done, either
# add "-e your@email" below, or poll with:
#   jcache pendingRequest
#   jcache status <requestIndex>
#
# Path convention (confirmed by hand, not assumed):
#   run >= 10000: /mss/hallb/hps/physrun2019/data/hpsecal_<run6>/hpsecal_<run6>.evio.*
#   run <  10000: /mss/hallb/hps/physrun2019/data/hpsecal_<run6>.evio.*   (flat, no subdir)

set BASE = /mss/hallb/hps/physrun2019/data
set RUNS = (9041 9044 9046 9048 9064 9108 9109 9179 10745 10748 10749 10750)

foreach RUN ($RUNS)
    set RUNPAD = `printf "%06d" $RUN`
    if ($RUN >= 10000) then
        set TARGET = "$BASE/hpsecal_${RUNPAD}/hpsecal_${RUNPAD}.evio.*"
    else
        set TARGET = "$BASE/hpsecal_${RUNPAD}.evio.*"
    endif
    echo "=== Run ${RUN}: jcache get $TARGET ==="
    # jcache get $TARGET
    jcache get $TARGET -e erbaz.khan@unh.edu    # uncomment and fill in to get notified per-run
end
