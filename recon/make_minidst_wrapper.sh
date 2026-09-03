#!/bin/bash
#
# make_minidst_wrapper.sh -- sources the HPS/ROOT environment then runs
# make_mini_dst on a single file. Needed because make_mini_dst is exposed by
# these setup scripts (a shell function/alias, not a standalone binary on
# PATH), and swif2's job command is a plain exec, not a login shell that
# would source them automatically.
#
# Usage: make_minidst_wrapper.sh <input.slcio> <output.root>

source /home/holtrop/bin/scripts/0functions.sh
source /home/holtrop/setup_HPS.sh
source /u/home/holtrop/root/bin/thisroot.sh

INFILE="$1"
OUTFILE="$2"

make_mini_dst -U -e -o "$OUTFILE" "$INFILE"
