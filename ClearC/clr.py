"""
This module contains functions for lexing, parsing, compiling
and assembling Clear code.
"""


def parse_source(source):
    """
    Given a string of Clear source code, returns its AST representation.
    """
    return ()


def compile_ast(ast):
    """
    Given an AST for a Clear program, returns a list of instructions
    to execute it.
    """
    return []


def assemble_code(code):
    """
    Given a list of Clear instructions, returns an assembled bytearray
    that can be saved to a .clr.b file.
    """
    assembled = bytearray()
    for instruction in code:
        assembled.append(instruction)
    return assembled
