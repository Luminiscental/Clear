
from enum import Enum
import re

class TokenType(Enum):

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
    IDENTIFIER = 19,
    STRING = 20,
    NUMBER = 21,
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
    ERR = 39,
    EOF = 40

class Token:

    def __init__(self, token_type, lexeme, line):
        self.token_type = token_type
        self.lexeme = lexeme
        self.line = line

def tokenize(source):

    for line in source.splitlines():
        without_comments = re.split("//", line)[0]
        words = [word.strip()
                    for word
                    in re.split("\\b", without_comments)
                    if word]
        if words:
            print(str(words))

