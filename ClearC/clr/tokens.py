import re
from enum import Enum
from collections import namedtuple
from clr.errors import emit_error
from clr.trie import Trie, TrieResult
from clr.values import DEBUG


class TokenType(Enum):

    # symbols
    LEFT_PAREN = 0
    RIGHT_PAREN = 1
    LEFT_BRACE = 2
    RIGHT_BRACE = 3
    COMMA = 4
    DOT = 5
    MINUS = 6
    PLUS = 7
    SEMICOLON = 8
    SLASH = 9
    STAR = 10
    BANG = 11
    BANG_EQUAL = 12
    EQUAL = 13
    EQUAL_EQUAL = 14
    GREATER = 15
    GREATER_EQUAL = 16
    LESS = 17
    LESS_EQUAL = 18
    # values
    IDENTIFIER = 19
    STRING = 20
    NUMBER = 21
    INTEGER_SUFFIX = 22
    # keywords
    AND = 23
    CLASS = 24
    ELSE = 25
    FALSE = 26
    FOR = 27
    FUNC = 28
    IF = 29
    OR = 30
    PRINT = 31
    RETURN = 32
    SUPER = 33
    THIS = 34
    TRUE = 35
    VAL = 36
    WHILE = 37
    # built-ins
    TYPE = 38
    INT = 39
    BOOL = 40
    NUM = 41
    STR = 42
    # special
    SPACE = 43
    EOF = 44
    ERR = 45


Token = namedtuple("Token", "token_type lexeme line")


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
    "while": TokenType.WHILE,
    "type": TokenType.TYPE,
    "int": TokenType.INT,
    "bool": TokenType.BOOL,
    "num": TokenType.NUM,
    "str": TokenType.STR,
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

    NUMBER = 0
    DECIMAL = 1
    STRING = 2
    IDENTIFIER = 3
    ANY = 4


def token_info(token):

    return f'<line {token.line}> "{token.lexeme}"'


def store_acc(token_type, acc, line, tokens):

    tokens.append(Token(token_type, "".join(acc), line))
    del acc[:]


def scan_number(char, acc, line, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None, line
    if char == ".":
        acc.append(char)
        return True, ScanState.DECIMAL, line
    if char == "i":
        store_acc(TokenType.NUMBER, acc, line, tokens)
        tokens.append(Token(TokenType.INTEGER_SUFFIX, "i", line))
        return True, ScanState.ANY, line
    store_acc(TokenType.NUMBER, acc, line, tokens)
    return False, ScanState.ANY, line


def scan_decimal(char, acc, line, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None, line
    store_acc(TokenType.NUMBER, acc, line, tokens)
    return False, ScanState.ANY, line


def scan_string(char, acc, line, tokens):

    if char == '"':
        acc.append(char)
        store_acc(TokenType.STRING, acc, line, tokens)
        return True, ScanState.ANY, line
    if char == "\n":
        line += 1
    acc.append(char)
    return True, None, line


def scan_identifier(char, acc, line, tokens, keyword_trie):

    if char.isalpha() or char.isdigit() or char == "_":
        result, _ = keyword_trie.step(char)
        acc.append(char)
        if result == TrieResult.FINISH:
            lexeme = "".join(acc)
            try:
                token_type = KEYWORD_TYPES[lexeme]
            except KeyError:
                emit_error(f'Expected keyword! <line {line}> "{lexeme}"')()
            store_acc(token_type, acc, line, tokens)
            return True, ScanState.ANY, line
        return True, None, line
    store_acc(TokenType.IDENTIFIER, acc, line, tokens)
    return False, ScanState.ANY, line


def scan_any(char, acc, line, tokens, keyword_trie):

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
                ScanState.NUMBER: scan_number,
                ScanState.DECIMAL: scan_decimal,
                ScanState.STRING: scan_string,
                ScanState.IDENTIFIER: lambda char, acc, line, tokens: scan_identifier(
                    char, acc, line, tokens, keyword_trie
                ),
            }.get(scan_state, emit_error(f"Unknown scanning state! {scan_state}"))(
                char, acc, line, tokens
            )
            if next_state:
                scan_state = next_state
            if consumed:
                continue
        next_state, line = scan_any(char, acc, line, tokens, keyword_trie)
        if next_state:
            scan_state = next_state

    if scan_state == ScanState.STRING:
        emit_error(f"Unclosed string literal reaches end of file!")()
    elif scan_state in (ScanState.NUMBER, ScanState.DECIMAL):
        store_acc(TokenType.NUMBER, acc, line, tokens)
    elif scan_state == ScanState.IDENTIFIER:
        store_acc(TokenType.IDENTIFIER, acc, line, tokens)

    tokens = [token for token in tokens if token.token_type != TokenType.SPACE]
    tokens.append(Token(TokenType.EOF, "", line))

    return tokens
