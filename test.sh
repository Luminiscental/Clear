#!/bin/sh

python crystal.py test/main.cy
g++ test/main.cpp -o test/main
test/main

