"""
Contains functions and definitions for lexing Clear code into a list of tokens.
"""

from typing import List, Iterable, Optional, Tuple

import enum
import re

import clr.errors as er


def tokenize_source(source: str) -> Tuple[List["Token"], List[er.CompileError]]:
    """
    Given a string of Clear source code, lexes it into a list of tokens.
    """
    skip_rules = [r"//.*", r"\s+"]
    consume_rules = [
        (r"[a-zA-Z_][a-zA-Z0-9_]*", TokenType.IDENTIFIER),
        (r"[0-9]+i", TokenType.INT_LITERAL),
        (r"[0-9]+(\.[0-9]+)?", TokenType.NUM_LITERAL),
        (r"\".*?\"", TokenType.STR_LITERAL),
        (r"==", TokenType.DOUBLE_EQUALS),
        (r"!=", TokenType.NOT_EQUALS),
        (r"<=", TokenType.LESS_EQUALS),
        (r"<", TokenType.LESS),
        (r">=", TokenType.GREATER_EQUALS),
        (r">", TokenType.GREATER),
        (r"=", TokenType.EQUALS),
        (r",", TokenType.COMMA),
        (r";", TokenType.SEMICOLON),
        (r":", TokenType.COLON),
        (r"\|", TokenType.VERT),
        (r"{", TokenType.LEFT_BRACE),
        (r"}", TokenType.RIGHT_BRACE),
        (r"\(", TokenType.LEFT_PAREN),
        (r"\)", TokenType.RIGHT_PAREN),
        (r"\?", TokenType.QUESTION_MARK),
        (r"\+", TokenType.PLUS),
        (r"-", TokenType.MINUS),
        (r"\*", TokenType.STAR),
        (r"/", TokenType.SLASH),
    ]
    fallback_rule = (r".", TokenType.ERROR)

    lexer = Lexer(source)
    lexer.run(consume_rules, skip_rules, fallback_rule)

    def keywordize(token: "Token") -> "Token":
        keyword_set = {
            TokenType.VAL,
            TokenType.FUNC,
            TokenType.VOID,
            TokenType.IF,
            TokenType.ELSE,
            TokenType.WHILE,
            TokenType.RETURN,
            TokenType.PRINT,
            TokenType.OR,
            TokenType.AND,
            TokenType.TRUE,
            TokenType.NIL,
            TokenType.FALSE,
        }

        keywords = {keyword.value: keyword for keyword in keyword_set}

        if token.kind == TokenType.IDENTIFIER:
            lexeme = str(token.lexeme)
            if lexeme in keywords:
                token.kind = keywords[lexeme]
        return token

    return (
        [keywordize(token) for token in lexer.tokens if token.kind != TokenType.ERROR],
        [
            er.CompileError(message=f"unexpected token {token}", regions=[token.lexeme])
            for token in lexer.tokens
            if token.kind == TokenType.ERROR
        ],
    )


@enum.unique
class TokenType(enum.Enum):
    """
    Enumerates the different types of tokens that can be in valid Clear source code.
    """

    # Non-definite tokens
    IDENTIFIER = "identifier"
    INT_LITERAL = "int"
    NUM_LITERAL = "num"
    STR_LITERAL = "str"
    # Keywords
    VAL = "val"
    FUNC = "func"
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    RETURN = "return"
    PRINT = "print"
    VOID = "void"
    OR = "or"
    AND = "and"
    TRUE = "true"
    FALSE = "false"
    NIL = "nil"
    # Symbols
    EQUALS = "="
    DOUBLE_EQUALS = "=="
    NOT_EQUALS = "!="
    LESS = "<"
    GREATER = ">"
    LESS_EQUALS = "<="
    GREATER_EQUALS = ">="
    COMMA = ","
    SEMICOLON = ";"
    COLON = ":"
    VERT = "|"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    QUESTION_MARK = "?"
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    # Special
    ERROR = "<ERROR>"

    def __str__(self) -> str:
        return str(self.value)


class Token:
    """
    Represents a single token within a string of Clear source code.
    """

    def __init__(self, kind: TokenType, lexeme: er.SourceView) -> None:
        self.kind = kind
        self.lexeme = lexeme

    def __repr__(self) -> str:
        return f"Token(kind={self.kind}, lexeme={self.lexeme})"

    def __str__(self) -> str:
        return str(self.lexeme)


class Lexer:
    """
    Class for walking over a source string and emitting tokens or skipping based on regex patterns.
    """

    tokens: List[Token]

    def __init__(self, source: str) -> None:
        self.source = source
        self.cursor = 0
        self.tokens = []

    def done(self) -> bool:
        """
        Returns whether the source has been fully used up or not.
        """
        return self.cursor == len(self.source)

    def consume(self, pattern: str, kind: TokenType) -> bool:
        """
        Check if the pattern is matched, and if it is emit it as a token and move after it.
        Returns whether the match was found.
        """
        match = re.match(pattern, self.source[self.cursor :])
        if match:
            literal = match.group(0)
            lexeme = er.SourceView(
                source=self.source,
                start=self.cursor,
                end=self.cursor + len(literal) - 1,
            )
            self.tokens.append(Token(kind=kind, lexeme=lexeme))
            self.cursor += len(literal)
            return True
        return False

    def skip(self, pattern: str) -> bool:
        """
        Check if the pattern is matched, and if it is move after it while leaving the start of
        the region before, so that the next consumed token will include this skipped region.
        Returns whether the match was found.
        """
        match = re.match(pattern, self.source[self.cursor :])
        if match:
            literal = match.group(0)
            self.cursor += len(literal)
            return True
        return False

    def run(
        self,
        consume_rules: Iterable[Tuple[str, TokenType]] = (),
        skip_rules: Iterable[str] = (),
        fallback: Optional[Tuple[str, TokenType]] = None,
    ) -> None:
        """
        Given an optional iterable of patterns to consume to token types, an optional iterable of
        patterns to skip, and an optional fallback pattern to consume to a fallback token type,
        loops over the source with these rules until reaching the end, or until reaching something
        it can't consume.
        """
        while not self.done():
            if (
                not any(self.skip(pattern) for pattern in skip_rules)
                and not any(
                    self.consume(pattern, kind) for pattern, kind in consume_rules
                )
                and (fallback is None or not self.consume(*fallback))
            ):
                break
