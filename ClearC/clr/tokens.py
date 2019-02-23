
from enum import Enum
import re
from collections import namedtuple
from clr.errors import ClrCompileError

class TokenType(Enum):

    # symbols
    LEFT_PAREN = 0,
    RIGHT_PAREN = 1,
    LEFT_BRACE = 2,
    RIGHT_BRACE = 3,
    COMMA = 4,
    DOT = 5,
    MINUS = 6,
    PLUS = 7,
    SEMICOLON = 8,
    SLASH = 9,
    STAR = 10,
    BANG = 11,
    BANG_EQUAL = 12,
    EQUAL = 13,
    EQUAL_EQUAL = 14,
    GREATER = 15,
    GREATER_EQUAL = 16,
    LESS = 17,
    LESS_EQUAL = 18,
    # values
    IDENTIFIER = 19,
    STRING = 20,
    NUMBER = 21,
    # keywords
    AND = 22,
    CLASS = 23,
    ELSE = 24,
    FALSE = 25,
    FOR = 26,
    FUNC = 27,
    IF = 28,
    OR = 29,
    PRINT = 30,
    RETURN = 31,
    SUPER = 32,
    THIS = 33,
    TRUE = 34,
    VAR = 35,
    VAL = 36,
    WHILE = 38,

class Token:

    def __init__(self, token_type, lexeme, line):
        self.token_type = token_type
        self.lexeme = lexeme
        self.line = line

    def __repr__(self):
        return "Token({}, '{}', {})".format(
                self.token_type, self.lexeme, self.line)

def tokenize(source):

    simple_tokens = {
        '+' : TokenType.PLUS,
        '-' : TokenType.MINUS,
        '*' : TokenType.STAR,
        '/' : TokenType.SLASH,
        ';' : TokenType.SEMICOLON,
        ',' : TokenType.COMMA,
        '.' : TokenType.DOT,
        '(' : TokenType.LEFT_PAREN,
        ')' : TokenType.RIGHT_PAREN,
        '{' : TokenType.LEFT_BRACE,
        '}' : TokenType.RIGHT_BRACE
    }

    SuffixType = namedtuple('SuffixType', 'present nonpresent')
    equal_suffix_tokens = {
        '!': SuffixType(TokenType.BANG_EQUAL, TokenType.BANG),
        '=': SuffixType(TokenType.EQUAL_EQUAL, TokenType.EQUAL),
        '<': SuffixType(TokenType.LESS_EQUAL, TokenType.LESS),
        '>': SuffixType(TokenType.GREATER_EQUAL, TokenType.GREATER)
    }

    # Replace // followed by a string of non-newline characters with nothing
    source = re.sub(r'//.*', '', source)
    tokens = []
    line = 1
    for char in source:
        if char in simple_tokens:
            tokens.append(Token(simple_tokens[char], char, line))

        elif char == '=' and tokens[-1].lexeme in equal_suffix_tokens:
            suffix_type = equal_suffix_tokens[tokens[-1].lexeme]
            tokens[-1] = Token(suffix_type.present,
                               tokens[-1].lexeme + '=',
                               line)

        elif char in equal_suffix_tokens:
            suffix_type = equal_suffix_tokens[char]
            tokens.append(Token(suffix_type.nonpresent, char, line))

        elif char.isdigit():
            pass # TODO

        elif char.isalpha():
            pass # TODO

        elif char == '\n':
            line += 1

        elif char == ' ':
            continue

        else:
            raise ClrCompileError("Unrecognized character '{}'".format(char))

    return tokens
