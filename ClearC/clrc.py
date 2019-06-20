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
import clr.ast as ast
import clr.printer as printer
import clr.resolver as resolver
import clr.typechecker as typechecker


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
    ptree, parse_errors = parser.parse_tokens(tokens)
    if parse_errors:
        print("Parse Errors:")
        print("--------")
        for parse_error in parse_errors:
            print(parse_error.display())
        print("--------")
        sys.exit(1)

    tree = ptree.to_ast()
    if isinstance(tree, ast.AstError):  # Shouldn't happen since we exit on parse errors
        print("Ast failed to form")
        sys.exit(1)

    print("Ast:")
    print("--------")
    printer.pprint(tree)
    print("--------")

    resolve_errors = resolver.resolve_names(tree)
    if resolve_errors:
        print("Resolve Errors:")
        print("--------")
        for resolve_error in resolve_errors:
            print(resolve_error)
        print("--------")
        sys.exit(1)

    type_errors = typechecker.check_types(tree)
    if type_errors:
        print("Type Errors:")
        print("--------")
        for type_error in type_errors:
            print(type_error)
        print("--------")
        sys.exit(1)

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
