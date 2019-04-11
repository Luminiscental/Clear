from clr.tokens import token_info


class Parser:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.errors = []

    def get_next(self):
        return self.tokens[self.index + 1]

    def get_current(self):
        return self.tokens[self.index]

    def get_prev(self):
        return self.tokens[self.index - 1]

    def current_info(self):
        return token_info(self.get_current())

    def prev_info(self):
        return token_info(self.get_prev())

    def advance(self):
        self.index += 1

    def check(self, token_type):
        return self.get_current().token_type == token_type

    def check_then(self, token_type):
        return self.get_next().token_type == token_type

    def check_one(self, possibilities):
        return self.get_current().token_type in possibilities

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
