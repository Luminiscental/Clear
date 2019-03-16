"""
This module provides a cli tool for compiling Clear source files
to bytecode files.
"""
import sys
from clr.errors import ClrCompileError
from clr.values import DEBUG, DONT_COMPILE
from clr.ast.parsing import Ast
from clr.assemble import assemble


def main():

    """
    The main entry point takes a command-line argument for the name of the
    source file, and reads it as source, compiles, and writes the bytecode to a .clr.b file
    using the given name.
    """

    if len(sys.argv) < 2:
        print("Please provide a file to compile")
        sys.exit(1)
    source_file_name = sys.argv[1] + ".clr"
    dest_file_name = source_file_name + ".b"
    if DEBUG:
        print("src:", source_file_name)
        print("dest:", dest_file_name)
    with open(source_file_name, "r") as source_file:
        source = source_file.read()
    try:
        ast = Ast.from_source(source)
        # TODO: Gen debug symbols
        if DONT_COMPILE:
            print("Didn't compile")
            return
        code = ast.compile()
        if DEBUG:
            print("Assembling:")
        byte_code = assemble(code)
    except ClrCompileError as compile_error:
        print("Could not compile:")
        print(compile_error)
    else:
        print("Compiled successfully")
        with open(dest_file_name, "wb") as dest_file:
            dest_file.write(byte_code)


if __name__ == "__main__":

    main()
