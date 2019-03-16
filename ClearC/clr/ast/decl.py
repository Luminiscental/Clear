from clr.tokens import TokenType
from clr.errors import parse_error
from clr.ast.stmt import BlockStmt, DeclNode, parse_stmt
from clr.ast.expr import parse_expr


def parse_decl(parser):
    if parser.check_one(VAL_TOKENS):
        return ValDecl(parser)
    if parser.check(TokenType.FUNC):
        return FuncDecl(parser)
    return parse_stmt(parser)


class FuncDecl(DeclNode):
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
        decl_visitor.visit_func_decl(self)


class ValDecl(DeclNode):
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
        decl_visitor.visit_val_decl(self)


VAL_TOKENS = {TokenType.VAL, TokenType.VAR}
