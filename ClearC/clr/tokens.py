"""
This module provides classes for storing information about tokens within
Clear source, as well as a tokenize function for converting a string of source
to a list of tokens.
"""
import re
from enum import Enum
from collections import namedtuple
from clr.errors import emit_error
from clr.trie import Trie, TrieResult
from clr.values import DEBUG


class TokenType(Enum):
    """
    This class enumerates the possible token types.
    """

    # symbols
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    COMMA = ","
    DOT = "."
    MINUS = "-"
    PLUS = "+"
    SEMICOLON = ";"
    SLASH = "/"
    STAR = "*"
    BANG = "!"
    BANG_EQUAL = "!="
    EQUAL = "="
    EQUAL_EQUAL = "=="
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="
    # values
    IDENTIFIER = "<identifier>"
    STRING = "<str>"
    NUMBER = "<number>"
    INTEGER_SUFFIX = "i"
    # keywords
    AND = "and"
    CLASS = "class"
    ELSE = "else"
    FALSE = "false"
    FOR = "for"
    FUNC = "func"
    IF = "if"
    OR = "or"
    PRINT = "print"
    RETURN = "return"
    SUPER = "super"
    THIS = "this"
    TRUE = "true"
    VAL = "val"
    VAR = "var"
    WHILE = "while"
    # special
    SPACE = "<whitespace>"
    EOF = "<eof>"
    ERR = "<error>"

    def __str__(self):
        return self.value


class Token(namedtuple("Token", "token_type lexeme line")):
    """
    This class wraps a namedtuple to store information about a single token.
    """

    def __str__(self):
        return self.lexeme


KEYWORD_TYPES = {
    "and": TokenType.AND,
    "class": TokenType.CLASS,
    "else": TokenType.ELSE,
    "false": TokenType.FALSE,
    "for": TokenType.FOR,
    "func": TokenType.FUNC,
    "if": TokenType.IF,
    "or": TokenType.OR,
    "print": TokenType.PRINT,
    "return": TokenType.RETURN,
    "super": TokenType.SUPER,
    "this": TokenType.THIS,
    "true": TokenType.TRUE,
    "val": TokenType.VAL,
    "var": TokenType.VAR,
    "while": TokenType.WHILE,
}

SIMPLE_TOKENS = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    ";": TokenType.SEMICOLON,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
}

SuffixType = namedtuple("SuffixType", "present nonpresent")

EQUAL_SUFFIX_TOKENS = {
    "!": SuffixType(TokenType.BANG_EQUAL, TokenType.BANG),
    "=": SuffixType(TokenType.EQUAL_EQUAL, TokenType.EQUAL),
    "<": SuffixType(TokenType.LESS_EQUAL, TokenType.LESS),
    ">": SuffixType(TokenType.GREATER_EQUAL, TokenType.GREATER),
}


class ScanState(Enum):

    """
    This class enumerates the possible states while scanning tokens.
    """

    NUMBER = 0
    DECIMAL = 1
    STRING = 2
    IDENTIFIER = 3
    ANY = 4


def token_info(token):

    """
    This function returns information about the given token as a string.
    """

    return f'<line {token.line}> "{token.lexeme}"'


def _store_acc(token_type, acc, line, tokens):

    tokens.append(Token(token_type, "".join(acc), line))
    del acc[:]


def _scan_number(char, acc, line, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None, line
    if char == ".":
        acc.append(char)
        return True, ScanState.DECIMAL, line
    if char == "i":
        _store_acc(TokenType.NUMBER, acc, line, tokens)
        tokens.append(Token(TokenType.INTEGER_SUFFIX, "i", line))
        return True, ScanState.ANY, line
    _store_acc(TokenType.NUMBER, acc, line, tokens)
    return False, ScanState.ANY, line


def _scan_decimal(char, acc, line, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None, line
    _store_acc(TokenType.NUMBER, acc, line, tokens)
    return False, ScanState.ANY, line


def _scan_string(char, acc, line, tokens):

    if char == '"':
        acc.append(char)
        _store_acc(TokenType.STRING, acc, line, tokens)
        return True, ScanState.ANY, line
    if char == "\n":
        line += 1
    acc.append(char)
    return True, None, line


def _scan_identifier(char, acc, line, tokens, keyword_trie):

    if char.isalpha() or char.isdigit() or char == "_":
        result, _ = keyword_trie.step(char)
        acc.append(char)
        if result == TrieResult.FINISH:
            lexeme = "".join(acc)
            try:
                token_type = KEYWORD_TYPES[lexeme]
            except KeyError:
                emit_error(f'Expected keyword! <line {line}> "{lexeme}"')()
            _store_acc(token_type, acc, line, tokens)
            return True, ScanState.ANY, line
        return True, None, line
    _store_acc(TokenType.IDENTIFIER, acc, line, tokens)
    return False, ScanState.ANY, line


def _scan_any(char, acc, line, tokens, keyword_trie):

    next_state = None

    if char in SIMPLE_TOKENS:
        tokens.append(Token(SIMPLE_TOKENS[char], char, line))
    elif (
        char == "="
        and tokens
        and tokens[-1].lexeme in EQUAL_SUFFIX_TOKENS
        and tokens[-1].token_type != TokenType.EQUAL_EQUAL
    ):
        suffix_type = EQUAL_SUFFIX_TOKENS[tokens[-1].lexeme]
        tokens[-1] = Token(suffix_type.present, tokens[-1].lexeme + "=", line)
    elif char in EQUAL_SUFFIX_TOKENS:
        suffix_type = EQUAL_SUFFIX_TOKENS[char]
        tokens.append(Token(suffix_type.nonpresent, char, line))
    elif char.isdigit():
        # TODO: Negative number literals?
        acc.append(char)
        next_state = ScanState.NUMBER
    elif char == '"':
        acc.append(char)
        next_state = ScanState.STRING
    elif char.isspace():
        if char == "\n":
            line += 1
        tokens.append(Token(TokenType.SPACE, " ", line))
    elif char.isalpha() or char == "_":
        if tokens and tokens[-1].token_type in KEYWORD_TYPES.values():
            acc.extend(tokens[-1].lexeme)
            del tokens[-1]
        else:
            keyword_trie.reset()
        keyword_trie.step(char)
        acc.append(char)
        next_state = ScanState.IDENTIFIER
    else:
        tokens.append(Token(TokenType.ERR, char, line))
        if DEBUG:
            print(f"Unrecognized character '{char}'")
    return next_state, line


def tokenize(source):

    """
    This function takes a string of Clear source code and returns a list
    of tokens from it, removing whitespace and comments.
    """

    # Replace // followed by a string of non-newline characters with nothing
    source = re.sub(r"//.*", "", source)

    keyword_trie = Trie(KEYWORD_TYPES)
    scan_state = ScanState.ANY
    tokens = []
    acc = []
    line = 1

    for char in source:
        if scan_state != ScanState.ANY:
            consumed, next_state, line = {
                ScanState.NUMBER: _scan_number,
                ScanState.DECIMAL: _scan_decimal,
                ScanState.STRING: _scan_string,
                ScanState.IDENTIFIER: lambda char, acc, line, tokens: _scan_identifier(
                    char, acc, line, tokens, keyword_trie
                ),
            }.get(scan_state, emit_error(f"Unknown scanning state! {scan_state}"))(
                char, acc, line, tokens
            )
            if next_state:
                scan_state = next_state
            if consumed:
                continue
        next_state, line = _scan_any(char, acc, line, tokens, keyword_trie)
        if next_state:
            scan_state = next_state

    if scan_state == ScanState.STRING:
        emit_error(f"Unclosed string literal reaches end of file!")()
    elif scan_state in (ScanState.NUMBER, ScanState.DECIMAL):
        _store_acc(TokenType.NUMBER, acc, line, tokens)
    elif scan_state == ScanState.IDENTIFIER:
        _store_acc(TokenType.IDENTIFIER, acc, line, tokens)

    tokens = [token for token in tokens if token.token_type != TokenType.SPACE]
    tokens.append(Token(TokenType.EOF, "", line))

    return tokens
