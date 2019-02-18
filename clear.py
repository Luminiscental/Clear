
from enum import Enum
import sys

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

    i = 0
    while i < len(source):
        c = source[i]
        if c in unambiguous_characters:
            result.append(Token(lexeme=c, token_type=unambiguous_characters[c], line=line))
            i = i + 1
            continue
        elif c in or_equals_characters:
            without_equals = or_equals_characters[c][0]
            with_equals = or_equals_characters[c][1]

            if i + 1 < len(source) and source[i + 1] == '=':
                result.append(Token(lexeme=c, token_type=with_equals, line=line))
                i = i + 1
            else:
                result.append(Token(lexeme=c, token_type=without_equals, line=line))
            i = i + 1
            continue
        elif c == '/':
            if i + 1 < len(source) and source[i + 1] == '/':
                while i < len(source) and source[i] != '\n':
                    i = i + 1
            else:
                result.append(Token(lexeme='/', token_type=TokenType.SLASH, line=line))
                i = i + 1
            continue
        elif c in flat_whitespace:
            i = i + 1
            continue
        elif c == '\n':
            line = line + 1
            i = i + 1
            continue
        elif c == '"':
            i = i + 1
            start = i
            while i < len(source) and source[i] != '"':
                if source[i] == '\n':
                    line = line + 1
                i = i + 1
            if i == len(source):
                raise CompileException("Unterminated string literal")
            result.append(Token(lexeme=source[start - 1:i + 1], token_type=TokenType.STRING, line=line, value=source[start:i]))
            i = i + 1
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

