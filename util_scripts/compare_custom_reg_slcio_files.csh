#!/bin/tcsh -f

# Check if exactly two arguments were provided
if ( $#argv != 2 ) then
    echo "Usage: $0 <directory1> <directory2>"
    exit 1
endif

set DIR1 = "$argv[1]"
set DIR2 = "$argv[2]"

# Extract the immediate directory (e.g., process_10103) safely handling trailing slashes
set SUB1 = `basename "$DIR1"`
set SUB2 = `basename "$DIR2"`

# Strip trailing slash if present, then extract the parent directory using awk
set PARENT1 = `echo "$DIR1" | sed 's/\/$//' | awk -F'/' '{print $(NF-1)}'`
set PARENT2 = `echo "$DIR2" | sed 's/\/$//' | awk -F'/' '{print $(NF-1)}'`

# Isolate just the trailing number/ID from the subdirectory (e.g., 10103)
set ID1 = `echo "$SUB1" | awk -F'_' '{print $NF}'`
set ID2 = `echo "$SUB2" | awk -F'_' '{print $NF}'`

# Fallback: if the subdirectory doesn't have an underscore, use the whole name
if ( "$ID1" == "" ) set ID1 = "$SUB1"
if ( "$ID2" == "" ) set ID2 = "$SUB2"

# Clean up parent name prefixes if they contain "_gains_recon"
set PREFIX1 = `echo "$PARENT1" | sed 's/_gains_recon//'`
set PREFIX2 = `echo "$PARENT2" | sed 's/_gains_recon//'`

# Construct the requested file names: e.g., regular_10103.txt and custom_10103.txt
set OUT1 = "${ID1}_{PREFIX1}.txt"
set OUT2 = "${ID2}_{PREFIX2}.txt"

# Clear out output files securely
true > "$OUT1"
true > "$OUT2"

# Use nonomatch so wildcards don't crash the script if empty
set nonomatch

echo "Processing $DIR1 -> $OUT1..."
set files1 = ( "$DIR1"/*.slcio )

if ( -e "$files1[1]" ) then
    foreach f ( $files1 )
        set name = `basename "$f"`

        echo "=== $name ===" >> "$OUT1"
        stat -c "Size: %s bytes" "$f" >> "$OUT1"

        # Build the exact log filename
        set log = "$DIR1/log_$name:r.txt"

        if ( -e "$log" ) then
            echo "Last line of log:" >> "$OUT1"
            tail -n 1 "$log" >> "$OUT1"
        else
            echo "Log file missing: log_$name:r.txt" >> "$OUT1"
        endif
        echo "" >> "$OUT1"
    end
endif

echo "Processing $DIR2 -> $OUT2..."
set files2 = ( "$DIR2"/*.slcio )

if ( -e "$files2[1]" ) then
    foreach f ( $files2 )
        set name = `basename "$f"`

        echo "=== $name ===" >> "$OUT2"
        stat -c "Size: %s bytes" "$f" >> "$OUT2"

        # Build the exact log filename for DIR2
        set log = "$DIR2/log_$name:r.txt"

        if ( -e "$log" ) then
            echo "Last line of log:" >> "$OUT2"
            tail -n 1 "$log" >> "$OUT2"
        else
            echo "Log file missing: log_$name:r.txt" >> "$OUT2"
        endif
        echo "" >> "$OUT2"
    end
endif

unset nonomatch

echo "--- Running Diff ---"
diff -y "$OUT1" "$OUT2"
