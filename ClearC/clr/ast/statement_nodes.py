from clr.tokens import TokenType, token_info
from clr.errors import ClrCompileError, parse_error, emit_error, sync_errors
from clr.ast.return_annotations import ReturnAnnotation
from clr.ast.index_annotations import IndexAnnotation
from clr.ast.expression_nodes import parse_expr, parse_grouping
from clr.ast.type_annotations import TypeAnnotation, BUILTINS
from clr.ast.type_nodes import FunctionType, parse_type


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


class StmtNode:  # pylint: disable=too-few-public-methods
    def __init__(self, parser):
        self.return_annotation = ReturnAnnotation()
        self.first_token = parser.get_current()
        self.type_annotation = TypeAnnotation()


class BlockStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected block!", parser))
        opener = parser.get_prev()
        self.declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            decl = parse_decl(parser)
            self.declarations.append(decl)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_block_stmt(self)


class ExprStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon to end expression statement!", parser),
        )

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_expr_stmt(self)


class RetStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.RETURN, parse_error("Expected return statement!", parser)
        )
        self.return_token = parser.get_prev()
        self.value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after return statement!", parser),
        )

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_ret_stmt(self)


class WhileStmt(StmtNode):
    def __init__(self, parser):
        # TODO: Break statements
        super().__init__(parser)
        parser.consume(
            TokenType.WHILE, parse_error("Expected while statement!", parser)
        )
        if not parser.check(TokenType.LEFT_BRACE):
            self.condition = parse_grouping(parser)
        else:
            self.condition = None
        self.block = BlockStmt(parser)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_while_stmt(self)


class IfStmt(StmtNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.IF, parse_error("Expected if statement!", parser))
        self.checks = [(parse_grouping(parser), BlockStmt(parser))]
        self.otherwise = None
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = parse_grouping(parser)
                other_block = BlockStmt(parser)
                self.checks.append((other_cond, other_block))
            else:
                self.otherwise = BlockStmt(parser)
                break

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_if_stmt(self)


class PrintStmt(StmtNode):
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

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_print_stmt(self)


def parse_decl(parser):
    try:
        if parser.check_one(VAL_TOKENS):
            return ValDecl(parser)
        if parser.check(TokenType.FUNC):
            return FuncDecl(parser)
        if parser.check(TokenType.STRUCT):
            return StructDecl(parser)
        return parse_stmt(parser)
    except ClrCompileError as error:
        if not parser.match(TokenType.EOF):
            parser.errors.append(str(error))
            parser.advance()


class DeclNode(StmtNode):  # pylint: disable=too-few-public-methods
    def __init__(self, parser):
        super().__init__(parser)
        self.index_annotation = IndexAnnotation()


class ValDecl(DeclNode):
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
        self.initializer = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_val_decl(self)


class FuncDecl(DeclNode):
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
        self.upvalues = []

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_func_decl(self)


class StructDecl(DeclNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(
            TokenType.STRUCT, parse_error("Expected struct declaration!", parser)
        )
        # Consume the name token
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected struct name!", parser)
        )
        self.name = parser.get_prev()
        self.fields = []
        self.methods = {}
        # Upvalues for the constructor
        self.upvalues = []
        parser.consume(
            TokenType.LEFT_BRACE, parse_error("Expected struct body!", parser)
        )
        # Consume the fields until we hit the closing brace
        while not parser.match(TokenType.RIGHT_BRACE):
            # Check if it's a method
            if parser.check(TokenType.FUNC) and parser.check_then(TokenType.IDENTIFIER):
                # Parse the function
                func_decl = FuncDecl(parser)
                # Put the declaration for the method in self.methods as the value for this field's index
                self.methods[len(self.fields)] = func_decl
                # Create a field for the method of the right type and name
                param_types = [param_type for (param_type, _) in func_decl.params]
                func_type = FunctionType(param_types, func_decl.return_type)
                func_pair = (func_type, func_decl.name)
                self.fields.append(func_pair)
            else:
                # Consume a type for the field
                field_type = parse_type(parser)
                # And then a name for the field
                parser.consume(
                    TokenType.IDENTIFIER, parse_error("Expected field name!", parser)
                )
                field_name = parser.get_prev()
                # If we haven't hit the end there must be a comma before the next field
                if not parser.check(TokenType.RIGHT_BRACE):
                    parser.consume(
                        TokenType.COMMA,
                        parse_error("Expected comma to delimit parameters!", parser),
                    )
                # Append the fields as (type, name) tuples
                pair = (field_type, field_name)
                self.fields.append(pair)

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_struct_decl(self)


VAL_TOKENS = {TokenType.VAL, TokenType.VAR}
