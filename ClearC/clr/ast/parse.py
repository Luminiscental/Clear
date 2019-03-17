"""
This module provides classes for parsing tokens into an AST representation of the code.

Classes:
    - Ast
    - Parser
"""
from clr.tokens import token_info


class Parser:
    """
    This class wraps a list of tokens to parse, with utility functions for common checks /
    procedures on the tokens.

    Fields:
        - index : the index of the current token to parse.
        - tokens : the list of all tokens to iterate over.

    Methods:
        - get_current
        - get_prev
        - current_info
        - prev_info
        - advance
        - check
        - check_one
        - match
        - consume
        - consume_one
    """

    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens

    def get_current(self):
        """
        This method returns the currently pointed to token.

        Returns:
            the token at the current index.
        """
        return self.tokens[self.index]

    def get_prev(self):
        """
        This method returns the previously pointed to token.

        Returns:
            the token at the index before the current one.
        """
        return self.tokens[self.index - 1]

    def current_info(self):
        """
        This method returns information about the current token as a string.

        Returns:
            string containing general information about the current token.
        """
        return token_info(self.get_current())

    def prev_info(self):
        """
        This method returns information about the previous token as a string.

        Returns:
            string containing general information about the previous token.
        """
        return token_info(self.get_prev())

    def advance(self):
        """
        This method advances to the next token, incrementing the index.
        """
        self.index += 1

    def check(self, token_type):
        """
        This method checks whether the current token is of a given token type.

        Parameters:
            - token_type : the type to check the current token against.

        Returns:
            boolean for whether the current token is of the given type.
        """
        return self.get_current().token_type == token_type

    def check_one(self, possibilities):
        """
        This method checks whether the current token is one of a given set of token types.

        Parameters:
            - possibilities : a set of possible token types to check the current token against.

        Returns:
            boolean for whether the current token matches one of the given types.
        """
        return self.get_current().token_type in possibilities

    def match(self, expected_type):
        """
        This method delegates to check, and if the current token did match advances to the next one,
        but otherwise does not advance.

        Parameters:
            - expected_type : the type to check for.

        Returns:
            boolean for whether the expected type was matched or not.
        """
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def match_one(self, possibilities):
        """
        This method delegates to check_one, and if the current token did match one of the
        possibilities advances to the next token, but otherwise does not advance.

        Parameters:
            - possibilities : a set of possible token tyeps to match against.

        Returns:
            boolean for whether any of the expected types was matched.
        """
        if not self.check_one(possibilities):
            return False
        self.advance()
        return True

    def consume(self, expected_type, err):
        """
        This method delegates to match, and if the current token did not match the expected type
        calls the err function.

        Parameters:
            - expected_type : the type to match against.
            - err : the function to call if the current token doesn't match.
        """
        if not self.match(expected_type):
            err()

    def consume_one(self, possibilities, err):
        """
        This method delegates to match_one, and if the current token did not match any of the
        expected types calls the err function.

        Parameters:
            - possibilities : A set of types to match against.
            - err : the function to call if the current token doesn't match any of the expected
                types.
        """
        if self.match_one(possibilities):
            return
        err()
