import struct
import sys
from clr.errors import ClrCompileError
from clr.compile import parse_source
from clr.values import DEBUG
from clr.ast import Ast


def main():

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
        if DEBUG:
            print("Compiling:")
        parser = parse_source(source)
        ast = Ast(parser)
    except ClrCompileError as e:
        print("Could not compile:")
        print(e)
    else:
        print("Compiled successfully")
        # TODO: Gen debug symbols


if __name__ == "__main__":

    main()
