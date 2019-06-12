"""
Contains functions for lexing, parsing and compiling Clear code.
"""

from typing import List, Tuple

import enum
import clr.bytecode as bc


class SourceView:
    """
    Represents a region within a Clear source string.
    """

    def __init__(self, source: str, start: int, end: int) -> None:
        self.start = start
        self.end = end
        self.source = source

    def __repr__(self) -> str:
        view = '"' + str(self) + '"'
        return f"SourceView[{view}]"

    def __str__(self) -> str:
        return self.source[self.start : self.end + 1]

    @staticmethod
    def full(source: str) -> "SourceView":
        return SourceView(source=source, start=0, end=len(source))


@enum.unique
class TokenType(enum.Enum):
    """
    Enumerates the different types of tokens that can be in valid Clear source code.
    """

    # Non-definite tokens
    IDENTIFIER = enum.auto()
    INT_LITERAL = enum.auto()
    NUM_LITERAL = enum.auto()
    STR_LITERAL = enum.auto()
    # Keywords
    NIL = enum.auto()
    TRUE = enum.auto()
    FALSE = enum.auto()
    # Symbols
    PLUS = enum.auto()
    # Special
    ERROR = enum.auto()


class Token:
    """
    Represents a single token within a string of Clear source code.
    """

    def __init__(self, kind: TokenType, region: SourceView, lexeme: SourceView) -> None:
        self.kind = kind
        self.region = region
        self.lexeme = lexeme

    def __repr__(self) -> str:
        return f"Token(kind={self.kind}, region={self.region}, lexeme={self.lexeme})"

    def __str__(self) -> str:
        return str(self.lexeme)


def tokenize_source(source: str) -> List[Token]:
    """
    Given a string of Clear source code, lexes it into a list of tokens.
    """
    fullview = SourceView.full(source)
    test_int = SourceView.full("27i")
    test_num = SourceView.full("5.3")
    test_string = SourceView.full('"hello"')
    return [
        Token(kind=TokenType.INT_LITERAL, region=test_int, lexeme=test_int),
        Token(kind=TokenType.NUM_LITERAL, region=test_num, lexeme=test_num),
        Token(kind=TokenType.STR_LITERAL, region=test_string, lexeme=test_string),
        Token(kind=TokenType.ERROR, region=fullview, lexeme=fullview),
    ]


class Ast:
    """
    Represents an AST of a Clear program.
    """

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens

    def __repr__(self) -> str:
        return f"Ast(tokens={self.tokens})"

    def __str__(self) -> str:
        return "".join(str(token) for token in self.tokens)


def compile_ast(ast: Ast) -> Tuple[List[bc.Constant], List[bc.Instruction]]:
    """
    Given an AST for a Clear program, returns the constants used and the instructions to execute it.
    """
    constants: List[bc.Constant] = []
    for token in ast.tokens:
        if token.kind == TokenType.INT_LITERAL:
            value_str = str(token.lexeme)[:-1]
            constants.append(int(value_str))
        elif token.kind == TokenType.NUM_LITERAL:
            value_str = str(token.lexeme)
            constants.append(float(value_str))
        elif token.kind == TokenType.STR_LITERAL:
            value_str = str(token.lexeme)[1:-1]
            constants.append(value_str)
    return (constants, [])
