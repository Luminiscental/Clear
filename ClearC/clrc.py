"""
Simple program to interface with the compiler.
Given a module name, it loads the .clr file, compiles it,
and exports the assembled .clr.b.
"""

from typing import List, Iterable, Sequence, Tuple

import sys

import clr.errors as er
import clr.bytecode as bc
import clr.lexer as lx
import clr.parser as ps
import clr.printer as pr
import clr.resolver as rs
import clr.typechecker as tc
import clr.controlflow as cf

DEBUG = True


def _get_filenames() -> Tuple[str, str]:
    if len(sys.argv) < 2:
        print("Please provide a module to compile")
        print("Usage:")
        print("$ clr <module name>")
        sys.exit(1)

    source_file_name = sys.argv[1] + ".clr"
    dest_file_name = source_file_name + ".b"
    if DEBUG:
        print(f"src: {source_file_name}")
        print(f"dest: {dest_file_name}")
    return source_file_name, dest_file_name


def _read_source(filename: str) -> str:
    try:
        with open(filename, "r") as source_file:
            return source_file.read()
    except FileNotFoundError:
        print(f"No file found for {filename}")
        sys.exit(1)


def _check_errors(error_name: str, errors: Iterable[er.CompileError]) -> None:
    def display(kind: str) -> None:
        print(f"{error_name} {kind}:")
        print("--------")
        for error in errors:
            print(error.display())
        print("--------")

    if any(error.severity == er.Severity.ERROR for error in errors):
        display("Errors")
        sys.exit(1)
    if any(error.severity == er.Severity.WARNING for error in errors):
        display("Warnings")


def _assemble_code(
    constants: Sequence[bc.Constant], instructions: Sequence[bc.Instruction]
) -> bytearray:
    try:
        return bc.assemble_code(constants, instructions)
    except bc.IndexTooLargeError:
        print("Couldn't assemble; too many variables")
        sys.exit(1)
    except bc.NegativeIndexError:
        print("Couldn't assemble; some variables were unresolved")
        sys.exit(1)
    except bc.StringTooLongError:
        print("Couldn't assemble; string literal was too long")
        sys.exit(1)


def main() -> None:
    """
    The main entry point function.
    """
    source_file_name, dest_file_name = _get_filenames()
    source = _read_source(source_file_name)

    tokens, lex_errors = lx.tokenize_source(source)
    _check_errors("Lex", lex_errors)

    tree = ps.parse_tokens(tokens)
    if isinstance(tree, er.CompileError):
        print("Parse Error:")
        print(tree.display())
        sys.exit(1)

    if DEBUG:
        print("Ast:")
        print("--------")
        pr.pprint(tree)
        print("--------")

    passes = [
        ("Resolve", rs.resolve_names),
        ("Type", tc.check_types),
        ("Control Flow", cf.check_flow),
    ]
    for pass_name, pass_func in passes:
        _check_errors(pass_name, pass_func(tree))

    constants: List[bc.Constant] = []
    instructions: List[bc.Instruction] = []

    assembled = _assemble_code(constants, instructions)

    with open(dest_file_name, "wb") as dest_file:
        dest_file.write(assembled)


if __name__ == "__main__":

    main()
