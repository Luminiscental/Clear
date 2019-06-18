"""
Simple program to interface with the compiler.
Given a module name, it loads the .clr file, compiles it,
and exports the assembled .clr.b.
"""

from typing import List

import sys

import clr.bytecode as bytecode
import clr.lexer as lexer
import clr.parser as parser


def main() -> None:
    """
    The main entry point function, everything is contained here.
    """

    if len(sys.argv) < 2:
        print("Please provide a file to compile")
        sys.exit(1)

    source_file_name = sys.argv[1] + ".clr"
    dest_file_name = source_file_name + ".b"
    print(f"src: {source_file_name}")
    print(f"dest: {dest_file_name}")

    try:
        with open(source_file_name, "r") as source_file:
            source = source_file.read()
    except FileNotFoundError:
        print(f"No file found for {source_file_name}")
        sys.exit(1)

    tokens = lexer.tokenize_source(source)
    parsetree, errors = parser.parse_tokens(tokens)
    if errors:
        print("Errors:")
        print("--------")
        for err in errors:
            print(err.display())
        print("--------")
        sys.exit(1)

    print("Parse tree:")
    print("--------")
    print(parsetree.pprint())
    print("--------")

    constants: List[bytecode.Constant] = []
    instructions: List[bytecode.Instruction] = []

    try:
        assembled = bytecode.assemble_code(constants, instructions)
    except bytecode.IndexTooLargeError:
        print("Couldn't assemble; too many variables")
        sys.exit(1)
    except bytecode.NegativeIndexError:
        print("Couldn't assemble; some variables were unresolved")
        sys.exit(1)
    except bytecode.StringTooLongError:
        print("Couldn't assemble; string literal was too long")
        sys.exit(1)

    with open(dest_file_name, "wb") as dest_file:
        dest_file.write(assembled)


if __name__ == "__main__":

    main()
