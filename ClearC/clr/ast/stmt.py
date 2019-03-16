from clr.ast.expr import AstNode
from clr.tokens import TokenType, token_info
from clr.errors import parse_error, emit_error
from clr.ast.expr import parse_expr
from clr.ast.resolve import ReturnAnnotation


def parse_stmt(parser):
    if parser.check(TokenType.PRINT):
        return PrintStmt(parser)
    if parser.check(TokenType.LEFT_BRACE):
        return BlockStmt(parser)
    if parser.check(TokenType.IF):
        return IfStmt(parser)
    if parser.check(TokenType.WHILE):
        return WhileStmt(parser)
    if parser.check(TokenType.RETURN):
        return RetStmt(parser)
    return ExprStmt(parser)


class DeclNode(AstNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.return_annotation = ReturnAnnotation()


class BlockStmt(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected block!", parser))
        opener = parser.get_prev()
        self.declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            from clr.ast.decl import parse_decl

            decl = parse_decl(parser)
            self.declarations.append(decl)

    def accept(self, stmt_visitor):
        stmt_visitor.visit_block_stmt(self)


class ExprStmt(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon to end expression statement!", parser),
        )
        self.token = self.value.token

    def accept(self, stmt_visitor):
        stmt_visitor.visit_expr_stmt(self)


class RetStmt(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.RETURN, parse_error("Expected return statement!", parser)
        )
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after return statement!", parser),
        )

    def accept(self, stmt_visitor):
        stmt_visitor.visit_ret_stmt(self)


class WhileStmt(DeclNode):
    def __init__(self, parser):
        # TODO: Break statements
        super().__init__(parser)
        parser.consume(
            TokenType.WHILE, parse_error("Expected while statement!", parser)
        )
        if not parser.check(TokenType.LEFT_BRACE):
            self.condition = parse_expr(parser)
        else:
            self.condition = None
        self.block = BlockStmt(parser)

    def accept(self, stmt_visitor):
        stmt_visitor.visit_while_stmt(self)


class IfStmt(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IF, parse_error("Expected if statement!", parser))
        self.checks = [(parse_expr(parser), BlockStmt(parser))]
        self.otherwise = None
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = parse_expr(parser)
                other_block = BlockStmt(parser)
                self.checks.append((other_cond, other_block))
            else:
                self.otherwise = BlockStmt(parser)
                break

    def accept(self, stmt_visitor):
        stmt_visitor.visit_if_stmt(self)


class PrintStmt(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.PRINT, parse_error("Expected print statement!", parser)
        )
        if not parser.match(TokenType.SEMICOLON):
            self.value = parse_expr(parser)
            parser.consume(
                TokenType.SEMICOLON,
                parse_error("Expected semicolon for print statement!", parser),
            )
        else:
            self.value = None

    def accept(self, stmt_visitor):
        stmt_visitor.visit_print_stmt(self)
