#!/bin/bash

# ----- VARIABLES TO SET ------
DB="/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan.db"
GAINS_FILE="/lustre24/expphy/volatile/hallb/hps/ekhan/FEE2019/analysis/cosmic_analysis/cosmic_gains_from_my_root_files/gains4db_zeroTest_sel1.txt"

# FIRST LINE IS HEADER, FORMAT: channel_id,gain
RUN_START=9000
RUN_END=10999
USER="erbaz"

LOG="Cosmic gains for 2019. Obtained from runs 9041, 9044, 9046, 9048, 9064, 9108, 9109, 9175, 9179, 10745, 10748, 10749, 10750"
DESCRIPTION="$LOG"
NOTES="$LOG"
# -----------------------------

# Diagnose
echo "DB path: $DB"
ls -la "$DB"
sqlite3 "$DB" ".tables"

# Insert collection
COLL_ID=$(sqlite3 "$DB" "INSERT INTO collections (table_name, log, description, created) \
VALUES ('ecal_gains', '$LOG', '$DESCRIPTION', datetime('now')); \
SELECT last_insert_rowid();")

echo "New collection ID: $COLL_ID"

# Insert all 442 gains
{
echo "BEGIN TRANSACTION;"
tail -n +2 "$GAINS_FILE" | while IFS=, read -r chan_id gain; do
    echo "INSERT INTO ecal_gains (collection_id, ecal_channel_id, gain) VALUES ($COLL_ID, $chan_id, $gain);"
done
echo "COMMIT;"
} | sqlite3 "$DB"

sqlite3 "$DB" "INSERT INTO conditions \
(run_start, run_end, created, created_by, notes, name, table_name, collection_id) \
VALUES ($RUN_START, $RUN_END, datetime('now'), '$USER', \
'$NOTES', 'ecal_gains', 'ecal_gains', $COLL_ID);"

echo "Verify:"
sqlite3 "$DB" "SELECT name, run_start, run_end, updated, collection_id FROM conditions \
WHERE table_name='ecal_gains' AND run_start <= $RUN_END AND run_end >= $RUN_START \
ORDER BY updated DESC;"