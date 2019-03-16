"""
This module provides classes for parsing tokens into an AST representation of the code.

Classes:
    - Ast
    - Parser
"""
from clr.tokens import TokenType, token_info
from clr.ast.decl import parse_decl
from clr.ast.expr import AstNode
from clr.ast.resolve import TypeResolver
from clr.ast.index import Indexer
from clr.ast.compile import Compiler
from clr.tokens import tokenize
from clr.values import DEBUG


class Ast(AstNode):
    """
    This class is the root node for the AST representation, initialized from a parser at the start
    of the tokenized source. On initialization the AST is indexed and resolved.

    It follows the grammar rule
    Ast : declaration* ;

    Superclasses:
        - AstNode

    Fields:
        - children : a list of the declaration nodes contained within the AST.

    Methods:
        - accept
        - compile

    Static methods:
        - from_source
    """

    def __init__(self, parser):
        super().__init__(parser)
        self.children = []
        while not parser.match(TokenType.EOF):
            self.children.append(parse_decl(parser))
        self.accept(TypeResolver())
        if DEBUG:
            print("Finished resolving")
        self.accept(Indexer())
        if DEBUG:
            print("Finished indexing")

    def compile(self):
        """
        This method compiles the AST as a program into bytecode.

        Returns:
            The total bytecode for the program, unassembled.
        """
        compiler = Compiler()
        self.accept(compiler)
        if DEBUG:
            print("Finished compiling")
        return compiler.flush_code()

    def accept(self, decl_visitor):
        """
        This method accepts a declaration visitor to the root node, to visit the entire tree.

        Parameters:
            - decl_visitor : the visitor to accept.
        """
        for child in self.children:
            child.accept(decl_visitor)

    @staticmethod
    def from_source(source):
        """
        This method takes a string of source and tokenizes it, loads the tokens into a parser,
        and initializes an AST from them, generating the entire program's AST.

        Parameters:
            - source : the string of source code to parse.

        Returns:
            the generated AST.
        """
        tokens = tokenize(source)
        parser = Parser(tokens)
        ast = Ast(parser)
        return ast


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
        This method delegates to match, and if the current token did not match any of the
        expected types calls the err function.

        Parameters:
            - possibilities : A set of types to match against.
            - err : the function to call if the current token doesn't match any of the expected
                types.
        """
        for possibility in possibilities:
            if self.match(possibility):
                return
        err()
