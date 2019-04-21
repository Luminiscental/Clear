from clr.tokens import Token, TokenType, token_info


class Parser:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.errors = []

    def __getitem__(self, offset):
        if self.index + offset >= len(self.tokens):
            return Token(TokenType.EOF, lexeme="", line=-1)
        return self.tokens[self.index + offset]

    def current_info(self):
        return token_info(self[0])

    def prev_info(self):
        return token_info(self[-1])

    def advance(self):
        self.index += 1

    def check(self, token_type):
        return self[0].token_type == token_type

    def check_then(self, token_type):
        return self[1].token_type == token_type

    def check_one(self, possibilities):
        return self[0].token_type in possibilities

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def match_one(self, possibilities):
        if not self.check_one(possibilities):
            return False
        self.advance()
        return True

    def consume(self, expected_type, err):
        if not self.match(expected_type):
            err()

    def consume_one(self, possibilities, err):
        if self.match_one(possibilities):
            return
        err()
