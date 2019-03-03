#!/bin/sh

clang-format -i -style="{BasedOnStyle: LLVM, IndentWidth: 4, IndentCaseLabels: true}" ClearVM/*.c ClearVM/*.h

black ClearC/
