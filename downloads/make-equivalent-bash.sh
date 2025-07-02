#!/bin/bash
set -e

# Check if largefile.bin exists; if not, create it
if [ ! -f largefile.bin ]; then
    echo "Generating largefile.bin..."
    dd if=/dev/zero of=largefile.bin bs=1M count=1024
fi

# Always regenerate hashes.txt
echo "Generating hashes.txt..."
sha1sum -b largefile.bin moby-dick.pdf > hashes.txt