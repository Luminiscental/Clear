"""
Contains functions for lexing, parsing and compiling Clear code.
"""

from typing import List, Tuple, Iterable, Optional

import enum
import re
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
        return f"SourceView[{str(self)}]"

    def __str__(self) -> str:
        return self.source[self.start : self.end + 1]

    @staticmethod
    def full(source: str) -> "SourceView":
        """
        Takes a string and makes a SourceView into the whole string.
        """
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


class Lexer:
    """
    Class for walking over a source string and emitting tokens or skipping based on regex patterns.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        self.start = 0
        self.end = 0
        self.tokens: List[Token] = []

    def done(self) -> bool:
        """
        Returns whether the source has been fully used up or not.
        """
        return self.end == len(self.source)

    def reset(self) -> None:
        """
        Resets the lexer to the start of its source
        """
        self.start = 0
        self.end = 0

    def consume(self, pattern: str, kind: TokenType) -> bool:
        """
        Check if the pattern is matched, and if it is emit it as a token and move after it.
        Returns whether the match was found.
        """
        match = re.match(pattern, self.source[self.end :])
        if match:
            literal = match.group(0)
            region = SourceView(
                source=self.source, start=self.start, end=self.end + len(literal) - 1
            )
            lexeme = SourceView(
                source=self.source, start=self.end, end=self.end + len(literal) - 1
            )
            self.tokens.append(Token(kind=kind, region=region, lexeme=lexeme))
            self.end += len(literal)
            self.start = self.end
            return True
        return False

    def skip(self, pattern: str) -> bool:
        """
        Check if the pattern is matched, and if it is move after it while leaving the start of
        the region before, so that the next consumed token will include this skipped region.
        Returns whether the match was found.
        """
        match = re.match(pattern, self.source[self.end :])
        if match:
            literal = match.group(0)
            self.end += len(literal)
            return True
        return False

    def run(
        self,
        consume_rules: Optional[Iterable[Tuple[str, TokenType]]] = None,
        skip_rules: Optional[Iterable[str]] = None,
        fallback: Optional[Tuple[str, TokenType]] = None,
    ) -> None:
        """
        Given an optional iterable of patterns to consume to token types, an optional iterable of
        patterns to skip, and an optional fallback pattern to consume to a fallback token type,
        loops over the source with these rules until reaching the end, or until reaching something
        it can't consume.
        """
        while not self.done():
            if consume_rules and any(
                self.consume(pattern, kind) for pattern, kind in consume_rules
            ):
                continue
            if skip_rules and any(self.skip(pattern) for pattern in skip_rules):
                continue
            if not fallback or not self.consume(fallback[0], fallback[1]):
                break


def tokenize_source(source: str) -> List[Token]:
    """
    Given a string of Clear source code, lexes it into a list of tokens.
    """
    skip_rules = [r"//.*", r"\s+"]
    consume_rules = [
        (r"[a-zA-Z_][a-zA-Z0-9_]*", TokenType.IDENTIFIER),
        (r"[0-9]+i", TokenType.INT_LITERAL),
        (r"[0-9]+(\.[0-9]+)?", TokenType.NUM_LITERAL),
        (r"\".*?\"", TokenType.STR_LITERAL),
    ]
    fallback_rule = (r".", TokenType.ERROR)

    lexer = Lexer(source)
    lexer.run(consume_rules, skip_rules, fallback_rule)
    return lexer.tokens


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
