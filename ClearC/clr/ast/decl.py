"""
This module provides classes / functions to form declaration nodes within the AST from parsing tokens.

Functions:
    - parse_decl

Classes:
    - DeclNode
    - FuncDecl
    - ValDecl
"""
from clr.tokens import TokenType
from clr.errors import parse_error
from clr.ast.stmt import BlockStmt, StmtNode, parse_stmt
from clr.ast.expr import parse_expr
from clr.ast.index import IndexAnnotation


def parse_decl(parser):
    """
    This function parses a declaration node for the AST from the parser, emitting an error if the
    tokens don't form a valid declaration.

    The declaration follows the grammar rule
    declaration : ValDecl | FuncDecl | statement ;

    Parameters:
        - parser : the Parser instance to read tokens from.

    Returns:
        The Declaration node that was parsed.
    """
    if parser.check_one(VAL_TOKENS):
        return ValDecl(parser)
    if parser.check(TokenType.FUNC):
        return FuncDecl(parser)
    return parse_stmt(parser)


class DeclNode(StmtNode):
    """
    This class stores the index annotation for an AST node of a declaration, inheriting from
    StmtNode and to be inherited in any declaration node classes.

    Superclasses:
        - StmtNode

    Fields:
        - index_annotation : the index annotation of the declared value; by default unresolved.
    """

    def __init__(self, parser):
        super().__init__(parser)
        self.index_annotation = IndexAnnotation()


class FuncDecl(DeclNode):
    """
    This class represents an AST node for a function declaration, initialized from a parser.

    It follows the grammar rule
    FuncDecl : 'func' identifier '(' ( identifier identifier ( ',' identifier identifier )* )? ')' BlockStmt

    Superclasses:
        - DeclNode

    Fields:
        - name : the identifier token naming the declared function.
        - params : a list of (identifier, identifier) tuples for the parameters of the declared function.
        - block : the BlockStmt of code defining the function.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.FUNC, parse_error("Expected function declaration!", parser)
        )
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected function name!", parser)
        )
        self.name = parser.get_prev()
        parser.consume(
            TokenType.LEFT_PAREN,
            parse_error("Expected '(' to start function parameters!", parser),
        )
        self.params = []
        while not parser.match(TokenType.RIGHT_PAREN):
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected parameter type!", parser)
            )
            param_type = parser.get_prev()
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected parameter name!", parser)
            )
            param_name = parser.get_prev()
            pair = (param_type, param_name)
            self.params.append(pair)
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit arguments!", parser),
                )
        self.block = BlockStmt(parser)
        self.token = self.name

    def accept(self, decl_visitor):
        """
        This method accepts a declaration visitor to the node.

        Parameters:
            - decl_visitor : the visitor to accept.
        """
        decl_visitor.visit_func_decl(self)


class ValDecl(DeclNode):
    """
    This class reprents an AST node for a value declaration, initialized from a parser.

    It follows the grammar rule
    ValDecl : ( 'val' | 'var' ) identifier '=' expression ';' ;

    Superclasses:
        - DeclNode

    Fields:
        - mutable : boolean for whether the declared value is mutable.
        - name : the identifier token for the declared value.
        - value : the expression initializing the declared value.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume_one(
            VAL_TOKENS, parse_error("Expected value declaration!", parser)
        )
        self.mutable = parser.get_prev().token_type == TokenType.VAR
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected value name!", parser)
        )
        self.name = parser.get_prev()
        parser.consume(
            TokenType.EQUAL, parse_error("Expected '=' for value initializer!", parser)
        )
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )
        self.token = self.name

    def accept(self, decl_visitor):
        """
        This method accepts a declaration visitor to the node.

        Parameters:
            - decl_visitor : the visitor to accept.
        """
        decl_visitor.visit_val_decl(self)


VAL_TOKENS = {TokenType.VAL, TokenType.VAR}
