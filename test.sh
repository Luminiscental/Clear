#!/bin/sh

rm test/main.cpp
python crystal.py test/main.cy
#g++ test/main.cpp -o test/main
#test/main
cat test/main.cpp

