#!/bin/sh

if [ $# -lt 1 ]; then
    echo "Too few arguments!"
    echo "Usage: $0 <module name>"
elif [ $# -gt 1 ]; then
    echo "Too many arguments!"
    echo "Usage: $0 <module name>"
else
    set -e

    echo ""
    echo "-- Compiling VM --"

    pushd ClearVM
    mkdir -p build
    pushd build

    rm -f CMakeCache.txt
    cmake .. -DDEBUG_STACK=ON
    make

    echo ""
    echo "-- Running bytecode --"

    valgrind --leak-check=full ./clr ../../test/$1

    echo ""
    echo ""

    popd
    popd
fi
