#!/bin/bash

set -x
touch foo
stat foo
atdel -d -2 foo

rm foo

touch bar foo fuu
mv fuu foo
rm bar
stat foo
atdel
atdel --delete

atdel -d -2 foo
atdel --delete

atdel -d -2 nonexist
