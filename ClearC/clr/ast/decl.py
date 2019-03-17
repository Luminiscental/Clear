"""
This module provides classes / functions to form declaration nodes within the AST from parsing tokens.

Functions:
    - parse_decl

Classes:
    - DeclNode
    - FuncDecl
    - ValDecl
"""
from clr.tokens import TokenType, token_info
from clr.errors import parse_error, emit_error
from clr.ast.stmt import BlockStmt, parse_stmt
from clr.ast.tree import AstNode
from clr.ast.expr import parse_expr
from clr.ast.index import IndexAnnotation
from clr.ast.type import parse_type, BUILTINS


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


class DeclNode(AstNode):
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
    FuncDecl : 'func' identifier '(' ( type identifier ( ',' type identifier )* )? ')' type BlockStmt

    Superclasses:
        - DeclNode

    Fields:
        - name : the identifier token naming the declared function.
        - params : a list of (identifier, identifier) tuples for the parameters of the declared function.
        - return_type : the identifier token naming the return type.
        - block : the BlockStmt of code defining the function.

    Methods:
        - accept
    """

    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.FUNC, parse_error("Expected function declaration!", parser)
        )
        # Consume the name token
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected function name!", parser)
        )
        self.name = parser.get_prev()
        if self.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {self.name.lexeme}! This is reserved for the built-in function {self.name.lexeme}(). {token_info(self.name)}"
            )()
        parser.consume(
            TokenType.LEFT_PAREN,
            parse_error("Expected '(' to start function parameters!", parser),
        )
        self.params = []
        # Consume parameters until we hit the closing paren
        while not parser.match(TokenType.RIGHT_PAREN):
            # Consume a type for the parameter
            param_type = parse_type(parser)
            # And then a name for the parameter
            parser.consume(
                TokenType.IDENTIFIER, parse_error("Expected parameter name!", parser)
            )
            param_name = parser.get_prev()
            # Append the parameters as (type, name) tuples
            pair = (param_type, param_name)
            self.params.append(pair)
            # If we haven't hit the end there must be a comma before the next parameter
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )
        # Consume the return type
        self.return_type = parse_type(parser)
        # Consume the definition block
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
        # Consume the variable name
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected value name!", parser)
        )
        self.name = parser.get_prev()
        if self.name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {self.name.lexeme}! This is reserved for the built-in function {self.name.lexeme}(). {token_info(self.name)}"
            )()
        parser.consume(
            TokenType.EQUAL, parse_error("Expected '=' for value initializer!", parser)
        )
        # Consume the expression to initialize with
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
