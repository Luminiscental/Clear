#!/bin/sh

python ClearC/clrc.py test/main.cr

pushd ClearVM
mkdir -p build
pushd build

rm -f CMakeCache.txt
cmake ..
make
./clr ../../test/main.crb

popd
popd

