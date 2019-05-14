from clr.tokens import TokenType, token_info
from clr.errors import ClrCompileError, parse_error, emit_error, sync_errors
from clr.ast.return_annotations import ReturnAnnotation
from clr.ast.index_annotations import IndexAnnotation
from clr.ast.expression_nodes import parse_expr, parse_grouping
from clr.ast.type_annotations import TypeAnnotation, BUILTINS
from clr.ast.type_nodes import FunctionType, parse_type


def parse_stmt(parser):
    if parser.check(TokenType.PRINT):
        return PrintStmt.parse(parser)
    if parser.check(TokenType.LEFT_BRACE):
        return BlockStmt.parse(parser)
    if parser.check(TokenType.IF):
        return IfStmt.parse(parser)
    if parser.check(TokenType.WHILE):
        return WhileStmt.parse(parser)
    if parser.check(TokenType.RETURN):
        return RetStmt.parse(parser)
    return ExprStmt.parse(parser)


class StmtNode:  # pylint: disable=too-few-public-methods
    def __init__(self):
        self.return_annotation = ReturnAnnotation()
        self.type_annotation = TypeAnnotation()


class BlockStmt(StmtNode):
    def __init__(self, declarations):
        super().__init__()
        self.declarations = declarations

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.LEFT_BRACE, parse_error("Expected block!", parser))
        opener = parser[-1]
        declarations = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if parser.match(TokenType.EOF):
                emit_error(f"Unclosed block! {token_info(opener)}")()
            decl = parse_decl(parser)
            declarations.append(decl)
        return BlockStmt(declarations)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_block_stmt(self)


class ExprStmt(StmtNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

    @staticmethod
    def parse(parser):
        value = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon to end expression statement!", parser),
        )
        return ExprStmt(value)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_expr_stmt(self)


class RetStmt(StmtNode):
    def __init__(self, return_token, value):
        super().__init__()
        self.return_token = return_token
        self.value = value

    @staticmethod
    def parse(parser):
        parser.consume(
            TokenType.RETURN, parse_error("Expected return statement!", parser)
        )
        return_token = parser[-1]
        if not parser.match(TokenType.SEMICOLON):
            value = parse_expr(parser)
            parser.consume(
                TokenType.SEMICOLON,
                parse_error("Expected semicolon after return statement!", parser),
            )
        else:
            value = None
        return RetStmt(return_token, value)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_ret_stmt(self)


class WhileStmt(StmtNode):
    def __init__(self, condition, block):
        super().__init__()
        self.condition = condition
        self.block = block

    @staticmethod
    def parse(parser):
        # TODO: Break statements, for loops
        parser.consume(
            TokenType.WHILE, parse_error("Expected while statement!", parser)
        )
        if not parser.check(TokenType.LEFT_BRACE):
            condition = parse_grouping(parser)
        else:
            condition = None
        block = BlockStmt.parse(parser)
        return WhileStmt(condition, block)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_while_stmt(self)


class IfStmt(StmtNode):
    def __init__(self, checks, otherwise):
        super().__init__()
        self.checks = checks
        self.otherwise = otherwise

    @staticmethod
    def parse(parser):
        parser.consume(TokenType.IF, parse_error("Expected if statement!", parser))
        checks = [(parse_grouping(parser), BlockStmt.parse(parser))]
        otherwise = None
        while parser.match(TokenType.ELSE):
            if parser.match(TokenType.IF):
                other_cond = parse_grouping(parser)
                other_block = BlockStmt.parse(parser)
                checks.append((other_cond, other_block))
            else:
                otherwise = BlockStmt.parse(parser)
                break
        return IfStmt(checks, otherwise)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_if_stmt(self)


class PrintStmt(StmtNode):
    def __init__(self, value):
        super().__init__()
        self.value = value

    @staticmethod
    def parse(parser):
        parser.consume(
            TokenType.PRINT, parse_error("Expected print statement!", parser)
        )
        if not parser.match(TokenType.SEMICOLON):
            value = parse_expr(parser)
            parser.consume(
                TokenType.SEMICOLON,
                parse_error("Expected semicolon for print statement!", parser),
            )
        else:
            value = None
        return PrintStmt(value)

    @sync_errors
    def accept(self, stmt_visitor):
        stmt_visitor.visit_print_stmt(self)


def parse_decl(parser):
    try:
        if parser.check_one(VAL_TOKENS):
            return ValDecl.parse(parser)
        if parser.check(TokenType.FUNC) or parser.check(TokenType.AT):
            return FuncDecl.parse(parser)
        if parser.check(TokenType.STRUCT):
            return StructDecl.parse(parser)
        if parser.check(TokenType.PROP):
            return PropDecl.parse(parser)
        return parse_stmt(parser)
    except ClrCompileError as error:
        parser.errors.append(str(error))
        parser.advance()


class DeclNode(StmtNode):  # pylint: disable=too-few-public-methods
    def __init__(self):
        super().__init__()
        self.index_annotation = IndexAnnotation()


class ValDecl(DeclNode):
    def __init__(self, mutable, name, type_description, initializer):
        super().__init__()
        self.mutable = mutable
        self.name = name
        self.type_description = type_description
        self.initializer = initializer

    @staticmethod
    def parse(parser):
        parser.consume_one(
            VAL_TOKENS, parse_error("Expected value declaration!", parser)
        )
        mutable = parser[-1].token_type == TokenType.VAR
        # Consume the variable name
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected value name!", parser)
        )
        name = parser[-1]
        if name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {name.lexeme}! This is reserved for the built-in function {name.lexeme}(). {token_info(name)}"
            )()
        type_description = None
        if not parser.check(TokenType.EQUAL):
            type_description = parse_type(parser)
        parser.consume(
            TokenType.EQUAL, parse_error("Expected '=' for value initializer!", parser)
        )
        # Consume the expression to initialize with
        initializer = parse_expr(parser)
        parser.consume(
            TokenType.SEMICOLON,
            parse_error("Expected semicolon after value declaration!", parser),
        )
        return ValDecl(mutable, name, type_description, initializer)

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_val_decl(self)


def parse_params(parser):
    parser.consume(
        TokenType.LEFT_PAREN,
        parse_error("Expected '(' to start function parameters!", parser),
    )
    params = []
    # Consume parameters until we hit the closing paren
    while not parser.match(TokenType.RIGHT_PAREN):
        # Consume a type for the parameter
        param_type = parse_type(parser)
        # And then a name for the parameter
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected parameter name!", parser)
        )
        param_name = parser[-1]
        # Append the parameters as (type, name) tuples
        pair = (param_type, param_name)
        params.append(pair)
        # If we haven't hit the end there must be a comma before the next parameter
        if not parser.check(TokenType.RIGHT_PAREN):
            parser.consume(
                TokenType.COMMA,
                parse_error("Expected comma to delimit parameters!", parser),
            )
    return params


class FuncDecl(DeclNode):
    def __init__(self, name, params, return_type, block, decorator=None):
        super().__init__()
        self.name = name
        self.params = params
        self.return_type = return_type
        self.block = block
        self.upvalues = []
        self.decorator = decorator

    @staticmethod
    def parse(parser):
        # TODO: Multiple/chained decorators
        decorator = None
        if parser.match(TokenType.AT):
            decorator = parse_expr(parser)
        parser.consume(
            TokenType.FUNC, parse_error("Expected function declaration!", parser)
        )
        # Consume the name token
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected function name!", parser)
        )
        name = parser[-1]
        if name.lexeme in BUILTINS:
            emit_error(
                f"Invalid identifier name {name.lexeme}! This is reserved for the built-in function {name.lexeme}(). {token_info(name)}"
            )()
        params = parse_params(parser)
        # Consume the return type
        return_type = parse_type(parser)
        # Consume the definition block
        block = BlockStmt.parse(parser)
        return FuncDecl(name, params, return_type, block, decorator)

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_func_decl(self)


class PropDecl(DeclNode):
    def __init__(self, name, fields, methods):
        super().__init__()
        self.name = name
        self.fields = fields
        self.methods = methods

    @staticmethod
    def parse(parser):
        parser.consume(
            TokenType.PROP, parse_error("Expected property declaration!", parser)
        )
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected property name!", parser)
        )
        name = parser[-1]
        if name.lexeme in BUILTINS:
            emit_error(
                f"Invalid property name {token_info(name)}, this is reserved for the built-in function {name.lexeme}()"
            )()
        parser.consume(
            TokenType.LEFT_BRACE, parse_error("Expected property body!", parser)
        )
        methods = {}
        fields = []
        while not parser.match(TokenType.RIGHT_BRACE):
            if (
                parser.check(TokenType.AT)
                or parser.check(TokenType.FUNC)
                and parser.check_then(TokenType.IDENTIFIER)
            ):
                # It's a method
                parser.consume(
                    TokenType.FUNC, parse_error("Expected method declaration!", parser)
                )
                parser.consume(
                    TokenType.IDENTIFIER, parse_error("Expected method name!", parser)
                )
                method_name = parser[-1]
                params = parse_params(parser)
                return_type = parse_type(parser)
                methods[len(fields)] = (params, return_type)
                param_types = [param_type for (param_type, _) in params]
                func_type = FunctionType(param_types, return_type)
                pair = (func_type, method_name)
                fields.append(pair)
            else:
                field_type = parse_type(parser)
                parser.consume(
                    TokenType.IDENTIFIER, parse_error("Expected field name!", parser)
                )
                field_name = parser[-1]
                pair = (field_type, field_name)
                fields.append(pair)
            if not parser.check(TokenType.RIGHT_BRACE):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit members!", parser),
                )
        return PropDecl(name, fields, methods)

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_prop_decl(self)


class StructDecl(DeclNode):
    def __init__(self, name, fields, methods, props):
        super().__init__()
        self.name = name
        self.fields = fields
        self.methods = methods
        self.props = props
        # Upvalues for the constructor
        self.upvalues = []

    @staticmethod
    def parse(parser):
        parser.consume(
            TokenType.STRUCT, parse_error("Expected struct declaration!", parser)
        )
        # Consume the name token
        parser.consume(
            TokenType.IDENTIFIER, parse_error("Expected struct name!", parser)
        )
        name = parser[-1]
        if name.lexeme in BUILTINS:
            emit_error(
                f"Invalid struct name {token_info(name)}, this is reserved for the built-in function {name.lexeme}()"
            )()
        props = {}
        if parser.match(TokenType.WITH):
            while not parser.check(TokenType.LEFT_BRACE):
                parser.consume(
                    TokenType.IDENTIFIER, parse_error("Expected property name!", parser)
                )
                prop = parser[-1]
                if prop.lexeme in props:
                    emit_error(f"Duplicate property description {token_info(prop)}!")()
                field_map = {}
                if parser.match(TokenType.AS):
                    parser.consume(
                        TokenType.LEFT_BRACE,
                        parse_error("Expected field mapping block!", parser),
                    )
                    while not parser.match(TokenType.RIGHT_BRACE):
                        parser.consume(
                            TokenType.IDENTIFIER,
                            parse_error("Expected property field name!", parser),
                        )
                        param = parser[-1]
                        parser.consume(
                            TokenType.EQUAL,
                            parse_error("Expected '=' for field value", parser),
                        )
                        parser.consume(
                            TokenType.IDENTIFIER,
                            parse_error("Expected field name!", parser),
                        )
                        arg = parser[-1]
                        if param.lexeme in field_map:
                            emit_error(
                                f"Duplicate property field mapping {token_info(param)}"
                            )()
                        field_map[param.lexeme] = arg.lexeme
                        if not parser.check(TokenType.RIGHT_BRACE):
                            parser.consume(
                                TokenType.COMMA,
                                parse_error("Expected delimiting comma!", parser),
                            )
                props[prop.lexeme] = field_map
                if not parser.check(TokenType.LEFT_BRACE):
                    parser.consume(
                        TokenType.COMMA,
                        parse_error("Expected delimiting comma!", parser),
                    )
        fields = []
        methods = {}
        parser.consume(
            TokenType.LEFT_BRACE, parse_error("Expected struct body!", parser)
        )
        # Consume the fields until we hit the closing brace
        while not parser.match(TokenType.RIGHT_BRACE):
            # Check if it's a method
            if (
                parser.check(TokenType.AT)
                or parser.check(TokenType.FUNC)
                and parser.check_then(TokenType.IDENTIFIER)
            ):
                # Parse the function
                func_decl = FuncDecl.parse(parser)
                # Put the declaration for the method in self.methods as the value for this field's index
                methods[len(fields)] = func_decl
                # Create a field for the method of the right type and name
                param_types = [param_type for (param_type, _) in func_decl.params]
                func_type = FunctionType(param_types, func_decl.return_type)
                func_pair = (func_type, func_decl.name)
                fields.append(func_pair)
            else:
                # Consume a type for the field
                field_type = parse_type(parser)
                # And then a name for the field
                parser.consume(
                    TokenType.IDENTIFIER, parse_error("Expected field name!", parser)
                )
                field_name = parser[-1]
                # If we haven't hit the end there must be a comma before the next field
                if not parser.check(TokenType.RIGHT_BRACE):
                    parser.consume(
                        TokenType.COMMA,
                        parse_error("Expected comma to delimit members!", parser),
                    )
                # Append the fields as (type, name) tuples
                pair = (field_type, field_name)
                fields.append(pair)
        return StructDecl(name, fields, methods, props)

    @sync_errors
    def accept(self, decl_visitor):
        decl_visitor.visit_struct_decl(self)


VAL_TOKENS = {TokenType.VAL, TokenType.VAR}
