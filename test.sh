#!/bin/bash

set -x -e
pipx install -f .
touch foo
stat foo
atdel -d 2 foo
atdel -t "02/01 15:00" foo
atdel
atdel -v

lastid=$( atdel | tail -n 1 | awk '{ print $1 }' )
echo $lastid
atdel -D $lastid
inode=$( stat -c %i foo )
atdel --delete-file $( readlink -f foo ) || true
atdel --inode 1 --delete-file $( readlink -f foo )
atdel --inode $inode --delete-file $( readlink -f foo )

mkdir -p bar
touch bar/foo
atdel -d 2 bar
atdel
inode=$( stat -c %i bar )
atdel --inode $inode --delete-file $( readlink -f bar )


