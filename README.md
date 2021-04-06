### Clear

This is a project I made to learn about how compilers work. It's comprised of a python program `ClearC/`
to compile source code in the Clear language to bytecode for the C program `ClearVM/` to interpret. A
specification for this bytecode/VM can be found [here](ClearVM/SPEC.md), but there is no spec for
the source language for now, examples can be found in `test/`.

To run the `ClearC` compiler, interpret `clrc.py` as normal python3 inside the `ClearC` directory.
`ClearVM` needs to be built with cmake to get an executable `clr` that can run the generated
bytecode.
