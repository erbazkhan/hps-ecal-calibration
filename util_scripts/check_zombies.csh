#!/bin/bin/csh

# Check if a directory argument was provided
if ( $#argv < 1 ) then
    echo "Usage: $0 <directory>"
    exit 1
endif

set target_dir = $1

# Check if the directory exists
if ( ! -d $target_dir ) then
    echo "Error: Directory '$target_dir' does not exist."
    exit 1
endif

echo "Scanning $target_dir for zombie ROOT files..."
echo "--------------------------------------------"

# Loop through all .root files in the directory
foreach file ( ${target_dir}/*.root )
    # Ensure the glob actually matched files
    if ( ! -e "$file" ) then
        echo "No .root files found in $target_dir."
        exit 0
    endif

    # Run a quick one-liner in ROOT to check if the file is a Zombie
    # Redirect stderr to /dev/null to hide noisy ROOT warnings if the file is severely broken
    set is_zombie = `root -l -b -q -e "TFile *f = TFile::Open(\"$file\"); if(!f || f->IsZombie()) gSystem->Exit(1); else gSystem->Exit(0);" >& /dev/null; echo $status`

    if ( $is_zombie != 0 ) then
        echo "[ZOMBIE/CORRUPT] : $file"
    else
        echo "[OK]             : $file"
    endif
end
