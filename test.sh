#!/bin/sh

rm test/main.cpp
python clear.py test/main.cr
#g++ test/main.cpp -o test/main
#test/main
cat test/main.cpp

