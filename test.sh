#!/bin/sh

python ClearC/clrc.py test/main.clr

pushd ClearVM
mkdir -p build
pushd build

rm -f CMakeCache.txt
cmake ..
make
./clr ../../test/main.clr.b

popd
popd

