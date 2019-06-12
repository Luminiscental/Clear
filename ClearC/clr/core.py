"""
Contains functions for lexing, parsing, compiling and assembling Clear code.
"""

from typing import List, Tuple

import clr.bytecode as bc


class Ast:
    """
    Represents an AST of a Clear program.
    """

    def __init__(self, source: str) -> None:
        self.source = source


def parse_source(source: str) -> Ast:
    """
    Given a string of Clear source code, returns its AST representation.
    """
    return Ast(source)


def compile_ast(ast: Ast) -> Tuple[List[bc.Constant], List[bc.Instruction]]:
    """
    Given an AST for a Clear program, returns the constants used and the instructions to execute it.
    """
    return ([], [])
