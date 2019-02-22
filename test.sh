#!/bin/sh

echo ""
echo "-- Compiling test source --"

python ClearC/clrc.py test/main.clr

echo ""
echo "-- Compiling VM --"

pushd ClearVM
mkdir -p build
pushd build

rm -f CMakeCache.txt
cmake ..
make

echo ""
echo "-- Running bytecode --"

./clr ../../test/main.clr.b

echo ""
echo ""

popd
popd

