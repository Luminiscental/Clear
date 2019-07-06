"""
Simple program to interface with the compiler.
Given a module name, it loads the .clr file, compiles it,
and exports the assembled .clr.b.
"""

from typing import Iterable, Sequence, Tuple

import sys

import clr.errors as er
import clr.bytecode as bc
import clr.lexer as lx
import clr.parser as ps
import clr.printer as pr
import clr.resolver as rs
import clr.sequencer as sq
import clr.typechecker as tc
import clr.flowchecker as fc
import clr.indexer as ix
import clr.codegenerator as cg

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
        source_file = open(filename, "r")
    except FileNotFoundError:
        print(f"No file found for {filename}")
        sys.exit(1)

    with source_file:
        return source_file.read()


def _check_errors(error_name: str, errors: Iterable[er.CompileError]) -> None:
    def display(kind: str) -> None:
        print(f"{error_name} {kind}:")
        print("--------")
        for error in errors:
            print(error)
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


def main() -> None:
    """
    The main entry point function.
    """
    source_file_name, dest_file_name = _get_filenames()
    source = _read_source(source_file_name)

    if not source:
        print("No source code found in {source_file_name}")
        sys.exit(1)

    print("--------")

    # Lexical analysis
    tokens, lex_errors = lx.tokenize_source(source)
    _check_errors("Lexical", lex_errors)

    # Syntax analysis
    tree = ps.parse_tokens(tokens)
    if isinstance(tree, er.CompileError):
        _check_errors("Syntax", [tree])
        sys.exit(1)  # Even if it's only a warning we can't do much without the tree.

    if DEBUG:
        print("Ast:")
        print("--------")
        tree.accept(pr.AstPrinter())
        print("--------")

    # Semantic analysis
    subpasses = [
        ("Resolve", rs.DuplicateChecker()),
        ("Resolve", rs.NameTracker()),
        ("Resolve", rs.NameResolver()),
        ("Sequencing", sq.SequenceBuilder()),
        ("Sequencing", sq.SequenceWriter()),
        ("Type", tc.TypeChecker()),
        ("Control Flow", fc.FlowChecker()),
        ("Indexing", ix.UpvalueTracker()),
        ("Indexing", ix.IndexBuilder()),
        ("Indexing", ix.IndexWriter()),
    ]

    for name, visitor in subpasses:
        tree.accept(visitor)
        _check_errors(name, visitor.errors.get())

    if DEBUG:
        print("Sequenced Ast:")
        print("--------")
        tree.accept(pr.AstPrinter())
        print("--------")

    # Code generation
    assembled = _assemble_code(*cg.generate_code(tree))

    with open(dest_file_name, "wb") as dest_file:
        dest_file.write(assembled)


if __name__ == "__main__":

    main()
