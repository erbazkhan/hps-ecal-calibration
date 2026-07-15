#!/bin/bash

DB="/lustre24/expphy/volatile/hallb/hps/ekhan/ws/hps_conditions_ekhan_v4.db"
GAINS_FILE="/lustre24/expphy/volatile/hallb/hps/ekhan/FEE2019/custom_gains_recon/31976112_gain.txt"
RUN_START=10000
RUN_END=11000

# Diagnose
echo "DB path: $DB"
ls -la "$DB"
sqlite3 "$DB" ".tables"



# Insert collection
COLL_ID=$(sqlite3 "$DB" "INSERT INTO collections (table_name, log, description, created) \
  VALUES ('ecal_gains', 'Andrea FEE gains x new generated cosmic gains (31976112)', 'Andrea FEE gains (112) x new generated cosmic gains (3_1_976) with ADC2V set to 0.244 and from thirdTest and sel1 (31976112). 4 channels set to 0 (153,198,275,334). 267 has normal value.', datetime('now')); \
  SELECT last_insert_rowid();")
echo "New collection ID: $COLL_ID"

# Insert all 442 gains
{
  echo "BEGIN TRANSACTION;"
  tail -n +2 $GAINS_FILE | while IFS=, read -r chan_id gain; do
    echo "INSERT INTO ecal_gains (collection_id, ecal_channel_id, gain) VALUES ($COLL_ID, $chan_id, $gain);"
  done
  echo "COMMIT;"
} | sqlite3 $DB

# Link to run range — name must be 'ecal_gains' for conditions system to find it
sqlite3 $DB "INSERT INTO conditions \
  (run_start, run_end, created, created_by, notes, name, table_name, collection_id) \
  VALUES ($RUN_START, $RUN_END, datetime('now'), 'erbaz', \
  'Andrea FEE gains (112) x new generated cosmic gains (3_1_976) with ADC2V set to 0.244 and from thirdTest and sel1 (31976112). 4 channels set to 0 (153,198,275,334). 267 has normal value.', 'ecal_gains', 'ecal_gains', $COLL_ID);"

echo "Verify:"
sqlite3 $DB "SELECT name, run_start, run_end, updated, collection_id FROM conditions \
  WHERE table_name='ecal_gains' AND run_start <= $RUN_END AND run_end >= $RUN_START \
  ORDER BY updated DESC;"
