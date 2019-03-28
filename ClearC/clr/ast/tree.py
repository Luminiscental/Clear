import itertools
from collections import defaultdict, namedtuple
from clr.tokens import TokenType, token_info, tokenize
from clr.values import DEBUG, OpCode
from clr.errors import emit_error
from clr.constants import ClrUint, Constants
from clr.assemble import assembled_size
from clr.ast.visitor import DeclVisitor
from clr.ast.type_annotations import (
    TypeAnnotation,
    TypeAnnotationType,
    FunctionTypeAnnotation,
    INT_TYPE,
    NUM_TYPE,
    STR_TYPE,
    BOOL_TYPE,
    ANY_TYPE,
    BUILTINS,
)
from clr.ast.return_annotations import ReturnAnnotation, ReturnAnnotationType
from clr.ast.index_annotations import IndexAnnotationType
from clr.ast.parser import Parser
from clr.ast.expression_nodes import IdentExpr
from clr.ast.statement_nodes import StmtNode, parse_decl
from clr.ast.name_indexer import NameIndexer
from clr.ast.type_resolver import TypeResolver
from clr.ast.compiler import Compiler


class Ast:
    def __init__(self, parser):
        self.children = []
        while not parser.match(TokenType.EOF):
            decl = parse_decl(parser)
            self.children.append(decl)

        self.accept(TypeResolver())
        if DEBUG:
            print("Finished resolving")

        self.accept(NameIndexer())
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
