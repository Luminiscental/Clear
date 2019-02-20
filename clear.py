
from enum import Enum
import sys

def char_range(c1, c2):
    """Generates the characters from `c1` to `c2`, inclusive."""
    for c in range(ord(c1), ord(c2) + 1):
        yield chr(c)

class CompileException(Exception):
    pass

class TokenType(Enum):
    LEFT_PAREN = '('
    RIGHT_PAREN = ')'
    LEFT_BRACE = '{'
    RIGHT_BRACE = '}'
    COMMA = ','
    DOT = '.'
    SEMICOLON = ';'
    COLON = ':'
    PLUS = '+'
    MINUS = '-'
    STAR = '*'
    SLASH = '/'
    BANG = '!'
    BANG_EQUALS = '!='
    EQUALS = '='
    EQUALS_EQUALS = '=='
    GREATER = '>'
    GREATER_EQUALS = '>='
    LESS = '<'
    LESS_EQUALS = '<='

    # Literals
    IDENTIFIER = '<id>'
    STRING = '<str>'
    NUMBER = '<num>'

    # Keywords
    IF = 'if'
    ELSE = 'else'
    AND = 'and'
    OR = 'or'
    FOR = 'for'
    FUNC = 'func'
    VAL = 'val'
    CLASS = 'class'
    RETURN = 'return'

    # EOF
    EOF = '<eof>'

unambiguous_characters = { '(': TokenType.LEFT_PAREN,
                           ')': TokenType.RIGHT_PAREN,
                           '{': TokenType.LEFT_BRACE,
                           '}': TokenType.RIGHT_BRACE,
                           ',': TokenType.COMMA,
                           '.': TokenType.DOT,
                           ';': TokenType.SEMICOLON,
                           ':': TokenType.COLON,
                           '+': TokenType.PLUS,
                           '-': TokenType.MINUS,
                           '*': TokenType.STAR, }

or_equals_characters = { '>': (TokenType.GREATER, TokenType.GREATER_EQUALS),
                         '<': (TokenType.LESS, TokenType.LESS_EQUALS),
                         '!': (TokenType.BANG, TokenType.BANG_EQUALS) }

flat_whitespace = [ ' ', '\r', '\t' ]

class Token:
    def __init__(self, lexeme, line, token_type, value=None):
        self.lexeme = lexeme
        self.line = line
        self.token_type = token_type
        self.value = value

    def __str__(self):
        return str(self.token_type) + ": " + self.lexeme + " [" + str(self.line) + "]"

def tokenize(source):
    result = []
    line = 1

    def consume_unambiguous(i, character):
        return i + 1, Token(lexeme=c, token_type=unambiguous_characters[c], line=line)

    def consume_or_equals(i, character, next_character):
        types = or_equals_characters[character]

        if next_character == '=':
            return i + 2, Token(lexeme=character, token_type=types[1], line=line)
        else:
            return i + 1, Token(lexeme=character, token_type=types[0], line=line)

    def consume_slash(i, next_character):
        if next_character == '/':
            while i < len(source) and source[i] != '\n':
                i = i + 1
            return i, None
        else:
            return i + 1, Token(lexeme='/', token_type=TokenType.SLASH, line=line)

    def consume_string(i, line):
        i = i + 1
        start = i
        while i < len(source) and source[i] != '"':
            if source[i] == '\n':
                line = line + 1
            i = i + 1
        if i == len(source):
            raise CompileException("Unterminated string literal")
        return i + 1, line, Token(lexeme=source[start - 1:i + 1], token_type=TokenType.STRING, line=line, value=source[start:i])

    def consume_number(i, character):
        start = i
        while i < len(source) and source[i] in char_range('0', '9'):
            i = i + 1
        if i + 1 < len(source) and source[i] == '.' and source[i + 1] in char_range('0', '9'):
            i = i + 1
            while i < len(source) and source[i] in char_range('0', '9'):
                i = i + 1
        return i, Token(lexeme=source[start:i], token_type=TokenType.NUMBER, line=line, value=float(source[start:i]))

    i = 0
    while i < len(source):
        c = source[i]
        next_c = source[i + 1] if i + 1 < len(source) else ""
        if c in unambiguous_characters:
            i, token = consume_unambiguous(i, c)
            result.append(token)
            continue
        elif c in or_equals_characters:
            i, token = consume_or_equals(i, c, next_c)
            result.append(token)
            continue
        elif c == '/':
            i, token = consume_slash(i, next_c)
            if token:
                result.append(token)
            continue
        elif c in flat_whitespace:
            i = i + 1
            continue
        elif c == '\n':
            line = line + 1
            i = i + 1
            continue
        elif c == '"':
            i, line, token = consume_string(i, line)
            result.append(token)
            continue
        elif c in char_range('0', '9'):
            i, token = consume_number(i, c)
            result.append(token)
            continue
        else:
            raise CompileException("Un-recognized character: '" + c + "'")
        i = i + 1

    result.append(Token("", line, TokenType.EOF))
    return result

def parse_source(source):
    tokens = tokenize(source)

    print("Source:")
    print(source)

    print("Tokens:")
    for token in tokens:
        print(token)

def main():
    if len(sys.argv) < 2:
        print("Please provide a file to transpile")
        sys.exit(1)

    source_file_name = sys.argv[1]

    with open(source_file_name, "r") as source_file:
        source = source_file.read()
        try:
            parse_source(source)
        except CompileException as e:
            print("Could not compile:")
            print(e)

if __name__ == "__main__":
    main()

