import re
from enum import Enum
from collections import namedtuple
from clr.errors import emit_error
from clr.trie import Trie, TrieResult
from clr.values import DEBUG


class TokenType(Enum):

    # symbols
    LEFT_PAREN = "("
    RIGHT_PAREN = ")"
    LEFT_BRACE = "{"
    RIGHT_BRACE = "}"
    COMMA = ","
    DOT = "."
    MINUS = "-"
    PLUS = "+"
    AT = "@"
    SEMICOLON = ";"
    COLON = ":"
    SLASH = "/"
    STAR = "*"
    BANG = "!"
    QUESTION_MARK = "?"
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
    VOID = "void"
    STRUCT = "struct"
    ELSE = "else"
    FALSE = "false"
    FUNC = "func"
    IF = "if"
    OR = "or"
    PRINT = "print"
    RETURN = "return"
    THIS = "this"
    WITH = "with"
    AS = "as"
    TRUE = "true"
    VAL = "val"
    VAR = "var"
    WHILE = "while"
    NIL = "nil"
    # special
    SPACE = "<whitespace>"
    EOF = "<eof>"
    ERR = "<error>"

    def __str__(self):
        return self.value


class Token(namedtuple("Token", "token_type lexeme line")):
    def __str__(self):
        return self.lexeme


KEYWORD_TYPES = {
    TokenType.AND,
    TokenType.STRUCT,
    TokenType.ELSE,
    TokenType.FALSE,
    TokenType.FUNC,
    TokenType.IF,
    TokenType.OR,
    TokenType.PRINT,
    TokenType.RETURN,
    TokenType.THIS,
    TokenType.TRUE,
    TokenType.WITH,
    TokenType.AS,
    TokenType.VAL,
    TokenType.VAR,
    TokenType.WHILE,
    TokenType.VOID,
    TokenType.NIL,
}

KEYWORD_TYPES = {token_type.value: token_type for token_type in KEYWORD_TYPES}

SIMPLE_TOKENS = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "@": TokenType.AT,
    ";": TokenType.SEMICOLON,
    ":": TokenType.COLON,
    ",": TokenType.COMMA,
    ".": TokenType.DOT,
    "(": TokenType.LEFT_PAREN,
    ")": TokenType.RIGHT_PAREN,
    "{": TokenType.LEFT_BRACE,
    "}": TokenType.RIGHT_BRACE,
    "?": TokenType.QUESTION_MARK,
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


class Scanner:
    def __init__(self):
        self.line = 1
        self.acc = ""
        self.tokens = []
        self.state = ScanState.ANY
        self.keyword_trie = Trie(KEYWORD_TYPES)

    def store_acc(self, token_type):
        token = Token(token_type, self.acc, self.line)
        self.tokens.append(token)
        self.acc = ""

    def _scan_number(self, char):
        if char.isdigit():
            self.acc += char
            return True
        if char == ".":
            self.acc += char
            self.state = ScanState.DECIMAL
            return True
        if char == "i":
            self.store_acc(TokenType.NUMBER)
            self.tokens.append(Token(TokenType.INTEGER_SUFFIX, "i", self.line))
            self.state = ScanState.ANY
            return True
        self.store_acc(TokenType.NUMBER)
        self.state = ScanState.ANY
        return False

    def _scan_decimal(self, char):
        if char.isdigit():
            self.acc += char
            return True
        self.store_acc(TokenType.NUMBER)
        self.state = ScanState.ANY
        return False

    def _scan_string(self, char):
        self.acc += char
        if char == '"':
            self.store_acc(TokenType.STRING)
            self.state = ScanState.ANY
            return True
        if char == "\n":
            self.line += 1
        return True

    def _scan_identifier(self, char):
        if char.isalpha() or char.isdigit() or char == "_":
            result, _ = self.keyword_trie.step(char)
            self.acc += char
            if result == TrieResult.FINISH:
                lexeme = self.acc
                try:
                    token_type = KEYWORD_TYPES[lexeme]
                except KeyError:
                    emit_error(f'Expected keyword! <line {self.line}> "{lexeme}"')()
                self.store_acc(token_type)
                self.state = ScanState.ANY
            return True
        self.store_acc(TokenType.IDENTIFIER)
        self.state = ScanState.ANY
        return False

    def _start_string(self, char):
        self.acc += char
        self.state = ScanState.STRING

    def _start_identifier(self, char):
        continuing = False
        if self.tokens:
            last_token = self.tokens[-1]
            last_lexeme = last_token.lexeme
            last_type = last_token.token_type

            if last_type in KEYWORD_TYPES.values():
                self.acc += last_lexeme
                del self.tokens[-1]
                continuing = True

        if not continuing:
            self.keyword_trie.reset()

        self.keyword_trie.step(char)
        self.acc += char
        self.state = ScanState.IDENTIFIER

    def _scan_any(self, char):
        if self.tokens:
            last_token = self.tokens[-1]
            last_lexeme = last_token.lexeme
            last_type = last_token.token_type

        if char in SIMPLE_TOKENS:
            self.tokens.append(Token(SIMPLE_TOKENS[char], char, self.line))
        elif (
            char == "="
            and self.tokens
            and last_lexeme in EQUAL_SUFFIX_TOKENS
            and last_type != TokenType.EQUAL_EQUAL
        ):
            suffix_type = EQUAL_SUFFIX_TOKENS[last_lexeme]
            self.tokens[-1] = Token(suffix_type.present, last_lexeme + "=", self.line)
        elif char in EQUAL_SUFFIX_TOKENS:
            suffix_type = EQUAL_SUFFIX_TOKENS[char]
            self.tokens.append(Token(suffix_type.nonpresent, char, self.line))
        elif char.isdigit():
            # TODO: Negative number literals?
            self.acc += char
            self.state = ScanState.NUMBER
        elif char == '"':
            self._start_string(char)
        elif char.isspace():
            if char == "\n":
                self.line += 1
            self.tokens.append(Token(TokenType.SPACE, char, self.line))
        elif char.isalpha() or char == "_":
            self._start_identifier(char)
        else:
            self.tokens.append(Token(TokenType.ERR, char, self.line))
            if DEBUG:
                print(f"Unrecognized character '{char}'")
        return True

    def scan(self, char):
        if not {
            ScanState.ANY: self._scan_any,
            ScanState.DECIMAL: self._scan_decimal,
            ScanState.IDENTIFIER: self._scan_identifier,
            ScanState.NUMBER: self._scan_number,
            ScanState.STRING: self._scan_string,
        }[self.state](char):
            self._scan_any(char)

    def get_tokens(self):
        return [token for token in self.tokens if token.token_type != TokenType.SPACE]


def tokenize(source):

    # Replace // followed by a string of non-newline characters with nothing
    source = re.sub(r"//.*", "", source)
    scanner = Scanner()

    for char in source:
        scanner.scan(char)

    if scanner.state == ScanState.STRING:
        emit_error(f"Unclosed string literal reaches end of file!")()
    elif scanner.state in (ScanState.NUMBER, ScanState.DECIMAL):
        scanner.store_acc(TokenType.NUMBER)
    elif scanner.state == ScanState.IDENTIFIER:
        scanner.store_acc(TokenType.IDENTIFIER)

    tokens = scanner.get_tokens()
    tokens.append(Token(TokenType.EOF, "", scanner.line))

    return tokens
