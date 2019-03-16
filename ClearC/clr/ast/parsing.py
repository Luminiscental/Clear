from clr.tokens import TokenType, token_info
from clr.ast.decl import parse_decl
from clr.ast.expr import AstNode
from clr.ast.resolve import TypeResolver
from clr.ast.index import Indexer
from clr.ast.compile import Compiler
from clr.tokens import tokenize
from clr.values import DEBUG


class Ast(AstNode):
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
        compiler = Compiler()
        self.accept(compiler)
        if DEBUG:
            print("Finished compiling")
        return compiler.flush_code()

    def accept(self, decl_visitor):
        for child in self.children:
            child.accept(decl_visitor)

    @staticmethod
    def from_source(source):
        tokens = tokenize(source)
        parser = Parser(tokens)
        ast = Ast(parser)
        return ast


class Parser:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens

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

    def check_one(self, possibilities):
        return self.get_current().token_type in possibilities

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def consume(self, expected_type, err):
        if not self.match(expected_type):
            err()

    def consume_one(self, possibilities, err):
        for possibility in possibilities:
            if self.match(possibility):
                return
        err()
