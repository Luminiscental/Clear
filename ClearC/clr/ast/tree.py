from clr.tokens import TokenType, token_info, tokenize
from clr.ast.parse import Parser
from clr.values import DEBUG


class AstNode:
    """
    This class stores the representative token for an AST node, for use in referring to it by
    position in the source.

    Fields:
        - token : the representative token; by default the first token parsed in the node.

    Methods:
        get_info
    """

    def __init__(self, parser):
        self.token = parser.get_current()

    def get_info(self):
        """
        Returns information describing the representative token for this node.
        """
        return token_info(self.token)


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
        from clr.ast.decl import parse_decl

        self.children = []
        while not parser.match(TokenType.EOF):
            self.children.append(parse_decl(parser))
        from clr.ast.resolve import TypeResolver

        self.accept(TypeResolver())
        if DEBUG:
            print("Finished resolving")
        from clr.ast.index import Indexer

        self.accept(Indexer())
        if DEBUG:
            print("Finished indexing")

    def compile(self):
        """
        This method compiles the AST as a program into bytecode.

        Returns:
            The total bytecode for the program, unassembled.
        """
        from clr.ast.compile import Compiler

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
