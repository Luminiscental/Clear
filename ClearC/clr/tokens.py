
from enum import Enum
import re
from collections import namedtuple
from clr.errors import ClrCompileError
from clr.trie import Trie, TrieResult

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
    SPACE = 39

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

class Token:

    def __init__(self, token_type, lexeme, line):
        self.token_type = token_type
        self.lexeme = lexeme
        self.line = line

    def __repr__(self):
        return "Token({}, '{}', {})".format(
                self.token_type, self.lexeme, self.line)

class ParseState(Enum):

    NUMBER = 0,
    DECIMAL = 1,
    STRING = 2,
    IDENTIFIER = 3,
    ANY = 4

def store_acc(token_type, acc, line, tokens):

    tokens.append(Token(token_type, ''.join(acc), line))
    del acc[:]

def parse_number(char, acc, line, keyword_trie, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None
    elif char == '.':
        acc.append(char)
        return True, ParseState.DECIMAL
    else:
        store_acc(TokenType.NUMBER, acc, line, tokens)
        return False, ParseState.ANY

def parse_decimal(char, acc, line, keyword_trie, tokens):

    if char.isdigit():
        acc.append(char)
        return True, None
    else:
        store_acc(TokenType.NUMBER, acc, line, tokens)
        return False, ParseState.ANY

def parse_string(char, acc, line, keyword_trie, tokens):

    if char == '"':
        acc.append(char)
        store_acc(TokenType.STRING, acc, line, tokens)
        return True, ParseState.ANY
    else:
        acc.append(char)
        return True, None

def parse_identifier(char, acc, line, keyword_trie, tokens):

    if char.isalpha() or char.isdigit() or char == '_':
        result, _ = keyword_trie.step(char)
        acc.append(char)
        if result == TrieResult.FINISH:
            lexeme = ''.join(acc)
            store_acc(keyword_types[lexeme], acc, line, tokens)
            return True, ParseState.ANY
        return True, None
    else:
        store_acc(TokenType.IDENTIFIER, acc, line, tokens)
        return False, ParseState.ANY

def parse_any(char, acc, line, keyword_trie, tokens):

    if char in simple_tokens:
        tokens.append(Token(simple_tokens[char], char, line))
        return None
    elif (char == '=' and tokens
            and tokens[-1].lexeme in equal_suffix_tokens
            and tokens[-1].token_type != TokenType.EQUAL_EQUAL):
        suffix_type = equal_suffix_tokens[tokens[-1].lexeme]
        tokens[-1] = Token(suffix_type.present,
                           tokens[-1].lexeme + '=',
                           line)
        return None
    elif char in equal_suffix_tokens:
        suffix_type = equal_suffix_tokens[char]
        tokens.append(Token(suffix_type.nonpresent, char, line))
        return None
    elif char.isdigit():
        acc.append(char)
        return ParseState.NUMBER
    elif char == '"':
        acc.append(char)
        return ParseState.STRING
    elif char == '\n':
        line += 1
        return None
    elif char.isspace():
        tokens.append(Token(TokenType.SPACE, ' ', line))
        return None
    elif char.isalpha() or char == '_':
        if tokens and tokens[-1].token_type in keyword_types.values():
            acc.extend(tokens[-1].lexeme)
            del tokens[-1]
        else:
            keyword_trie.reset()
        keyword_trie.step(char)
        acc.append(char)
        return ParseState.IDENTIFIER
    else:
        raise ClrCompileError("Unrecognized character '{}'".format(char))

def tokenize(source):

    # Replace // followed by a string of non-newline characters with nothing
    source = re.sub(r'//.*', '', source)

    keyword_trie = Trie(keyword_types)
    parse_state = ParseState.ANY
    tokens = []
    acc = []
    line = 1

    for char in source:
        if parse_state != ParseState.ANY:
            consumed, next_state = {
                ParseState.NUMBER : parse_number,
                ParseState.DECIMAL : parse_decimal,
                ParseState.STRING : parse_string,
                ParseState.IDENTIFIER : parse_identifier
            }[parse_state](char, acc, line, keyword_trie, tokens)
            if next_state:
                parse_state = next_state
            if consumed:
                continue
        next_state = parse_any(char, acc, line, keyword_trie, tokens)
        if next_state:
            parse_state = next_state

    tokens = [token for token in tokens
            if token.token_type != TokenType.SPACE]

    return tokens

