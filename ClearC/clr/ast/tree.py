from clr.values import DEBUG
from clr.tokens import TokenType, tokenize
from clr.errors import emit_error
from clr.ast.parser import Parser
from clr.ast.name_indexer import NameIndexer
from clr.ast.type_resolver import TypeResolver
from clr.ast.compiler import Compiler
from clr.ast.statement_nodes import parse_decl


class Ast:
    def __init__(self, parser):
        self.children = []
        while not parser.match(TokenType.EOF):
            decl = parse_decl(parser)
            self.children.append(decl)
        if parser.errors:
            emit_error("Parse errors:\n" + "\n".join(parser.errors))()
        if DEBUG:
            print("-- Finished parsing")

        resolver = TypeResolver()
        self.accept(resolver)
        if resolver.errors:
            emit_error("Resolve errors:\n" + "\n".join(resolver.errors))()
        if DEBUG:
            print("-- Finished resolving")

        indexer = NameIndexer()
        self.accept(indexer)
        if indexer.errors:
            emit_error("Index errors:\n" + "\n".join(indexer.errors))()
        if DEBUG:
            print("-- Finished indexing")

    def compile(self):
        compiler = Compiler()
        self.accept(compiler)
        if compiler.errors:
            emit_error("Compile errors:\n" + "\n".join(compiler.errors))()
        if DEBUG:
            print("-- Finished compiling")
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
