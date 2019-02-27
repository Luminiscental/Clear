
from collections import namedtuple, defaultdict
from enum import Enum

class OpCode(Enum):

    STORE_CONST = 0
    NUMBER = 1
    STRING = 2
    PRINT = 3
    LOAD_CONST = 4
    NEGATE = 5
    ADD = 6
    SUBTRACT = 7
    MULTIPLY = 8
    DIVIDE = 9
    RETURN = 10
    POP = 11
    DEFINE = 12
    TRUE = 13
    FALSE = 14
    NOT = 15
    LESS = 16
    NLESS = 17
    GREATER = 18
    NGREATER = 19
    EQUAL = 20
    NEQUAL = 21

    def __int__(self):
        return self.value

    def __str__(self):
        return 'OP_' + self.name

class Precedence(Enum):

    NONE = 0
    ASSIGNMENT = 1
    OR = 2
    AND = 3
    EQUALITY = 4
    COMPARISON = 5
    TERM = 6
    FACTOR = 7
    UNARY = 8
    CALL = 9
    PRIMARY = 10

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __cmp__(self, other):
        if self.value == other.value:
            return 0
        elif self.value < other.value:
            return -1
        else:
            return 1

    def next(self):
        return Precedence(self.value + 1)

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
    # special
    SPACE = 39,
    EOF = 40

keyword_types = {

    'and' : TokenType.AND,
    'class' : TokenType.CLASS,
    'else' : TokenType.ELSE,
    'false' : TokenType.FALSE,
    'for' : TokenType.FOR,
    'func' : TokenType.FUNC,
    'if' : TokenType.IF,
    'or' : TokenType.OR,
    'print' : TokenType.PRINT,
    'return' : TokenType.RETURN,
    'super' : TokenType.SUPER,
    'this' : TokenType.THIS,
    'true' : TokenType.TRUE,
    'var' : TokenType.VAR,
    'val' : TokenType.VAL,
    'while' : TokenType.WHILE
}

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

class ParseRule:

    def __init__(self, prefix=None, infix=None, precedence=Precedence.NONE):
        self.prefix = prefix
        self.infix = infix
        self.precedence = precedence

    def fill(self, err):
        if not self.prefix:
            self.prefix = err
        if not self.infix:
            self.infix = err

def pratt_table(parser):

    return defaultdict(ParseRule, {
        TokenType.LEFT_PAREN: ParseRule(
            prefix=parser.finish_grouping,
            precedence=Precedence.CALL
        ),
        TokenType.MINUS: ParseRule(
            prefix=parser.finish_unary,
            infix=parser.finish_binary,
            precedence=Precedence.TERM
        ),
        TokenType.PLUS: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.TERM
        ),
        TokenType.SLASH: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.FACTOR
        ),
        TokenType.STAR: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.FACTOR
        ),
        TokenType.NUMBER: ParseRule(
            prefix=parser.consume_number
        ),
        TokenType.STRING: ParseRule(
            prefix=parser.consume_string
        ),
        TokenType.TRUE: ParseRule(
            prefix=parser.consume_boolean
        ),
        TokenType.FALSE: ParseRule(
            prefix=parser.consume_boolean
        ),
        TokenType.AND: ParseRule(
            precedence=Precedence.AND
        ),
        TokenType.OR: ParseRule(
            precedence=Precedence.OR
        ),
        TokenType.BANG: ParseRule(
            prefix=parser.finish_unary
        ),
        TokenType.EQUAL_EQUAL: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.EQUALITY
        ),
        TokenType.BANG_EQUAL: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.EQUALITY
        ),
        TokenType.LESS: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.COMPARISON
        ),
        TokenType.GREATER_EQUAL: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.COMPARISON
        ),
        TokenType.GREATER: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.COMPARISON
        ),
        TokenType.LESS_EQUAL: ParseRule(
            infix=parser.finish_binary,
            precedence=Precedence.COMPARISON
        ),
    })

