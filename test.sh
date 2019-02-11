#!/bin/sh

python clear.py test/main.cr
g++ test/main.cpp -o test/main
test/main

