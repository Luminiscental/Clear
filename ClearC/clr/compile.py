from clr.tokens import TokenType, token_info, tokenize
from clr.errors import emit_error
from clr.assemble import assemble
from clr.constants import Constants, ClrNum, ClrInt, ClrStr
from clr.values import OpCode, Precedence, pratt_table, DEBUG


class GlobalVariables:
    def __init__(self):
        self.indices = {}
        self.index = 0

    def get_name(self, name):
        try:
            return self.indices[name]
        except KeyError:
            emit_error(f"Reference to undefined global {name}!")()

    def add_name(self, name):
        if DEBUG:
            print(f"Adding global {self.index}:{name}")
        self.indices[name] = self.index
        self.index += 1
        return self.indices[name]


class Program:
    def __init__(self):
        self.code_list = []
        self.global_variables = GlobalVariables()

    def load_constant(self, constant):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def define_name(self, name):
        self.code_list.append(OpCode.DEFINE_GLOBAL)
        index = self.global_variables.add_name(name)
        self.code_list.append(index)

    def load_name(self, name):
        self.code_list.append(OpCode.LOAD_GLOBAL)
        index = self.global_variables.get_name(name)
        self.code_list.append(index)

    def flush(self):
        return self.code_list


class Cursor:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.constants = Constants()
        self.program = Program()

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

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def consume(self, expected_type, message):
        if not self.match(expected_type):
            emit_error(message)()

    def flush(self):
        self.program.simple_op(OpCode.RETURN)
        return self.constants.flush() + self.program.flush()


class Parser(Cursor):
    def get_rule(self, token):
        return pratt_table(
            self, err=emit_error(f"Expected expression! {token_info(token)}")
        )[token.token_type]

    def current_precedence(self):
        return self.get_rule(self.get_current()).precedence

    def consume_builtin(self):
        builtin = self.get_prev()
        self.consume(
            TokenType.LEFT_PAREN,
            f"Expected parameter to built-in function! {self.prev_info()}",
        )
        self.finish_grouping()
        {
            TokenType.TYPE: lambda: self.program.simple_op(OpCode.TYPE),
            TokenType.INT: lambda: self.program.simple_op(OpCode.INT),
            TokenType.BOOL: lambda: self.program.simple_op(OpCode.BOOL),
            TokenType.NUM: lambda: self.program.simple_op(OpCode.NUM),
            TokenType.STR: lambda: self.program.simple_op(OpCode.STR),
        }.get(
            builtin.token_type,
            emit_error(f"Expected built-in function! {self.prev_info()}"),
        )()

    def consume_boolean(self):
        token = self.get_prev()
        err = emit_error(f"Expected boolean token! {self.prev_info()}")
        {
            TokenType.TRUE: lambda: self.program.simple_op(OpCode.TRUE),
            TokenType.FALSE: lambda: self.program.simple_op(OpCode.FALSE),
        }.get(token.token_type, err)()

    def consume_number(self):
        token = self.get_prev()
        if token.token_type != TokenType.NUMBER:
            emit_error(f"Expected number token! {self.prev_info()}")()
        if self.match(TokenType.INTEGER_SUFFIX):
            try:
                value = ClrInt(token.lexeme)
            except ValueError:
                emit_error(f"Integer literal must be an integer! {self.prev_info()}")()
        else:
            try:
                value = ClrNum(token.lexeme)
            except ValueError:
                emit_error(f"Number literal must be a number! {self.prev_info()}")()
        const_index = self.constants.add(value)
        self.program.load_constant(const_index)

    def consume_string(self):
        token = self.get_prev()
        if token.token_type != TokenType.STRING:
            emit_error(f"Expected string token! {self.prev_info()}")()

        total = [token]
        while self.match(TokenType.STRING):
            total.append(self.get_prev())

        string = ClrStr('"'.join(map(lambda t: t.lexeme[1:-1], total)))
        const_index = self.constants.add(string)
        self.program.load_constant(const_index)

    def consume_precedence(self, precedence):
        self.advance()
        self.get_rule(self.get_prev()).prefix()
        while precedence <= self.current_precedence():
            self.advance()
            self.get_rule(self.get_prev()).infix()

    def finish_grouping(self):
        self.consume_expression()
        self.consume(
            TokenType.RIGHT_PAREN, f"Expected ')' after expression! {self.prev_info()}"
        )

    def finish_unary(self):
        op_token = self.get_prev()
        self.consume_precedence(Precedence.UNARY)
        {
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.NEGATE),
            TokenType.BANG: lambda: self.program.simple_op(OpCode.NOT),
        }.get(
            op_token.token_type,
            emit_error(f"Expected unary operator! {self.prev_info()}"),
        )()

    def finish_binary(self):
        op_token = self.get_prev()
        rule = self.get_rule(op_token)
        self.consume_precedence(rule.precedence.next())
        {
            TokenType.PLUS: lambda: self.program.simple_op(OpCode.ADD),
            TokenType.MINUS: lambda: self.program.simple_op(OpCode.SUBTRACT),
            TokenType.STAR: lambda: self.program.simple_op(OpCode.MULTIPLY),
            TokenType.SLASH: lambda: self.program.simple_op(OpCode.DIVIDE),
            TokenType.EQUAL_EQUAL: lambda: self.program.simple_op(OpCode.EQUAL),
            TokenType.BANG_EQUAL: lambda: self.program.simple_op(OpCode.NEQUAL),
            TokenType.LESS: lambda: self.program.simple_op(OpCode.LESS),
            TokenType.GREATER_EQUAL: lambda: self.program.simple_op(OpCode.NLESS),
            TokenType.GREATER: lambda: self.program.simple_op(OpCode.GREATER),
            TokenType.LESS_EQUAL: lambda: self.program.simple_op(OpCode.NGREATER),
        }.get(
            op_token.token_type,
            emit_error(f"Expected binary operator! {self.prev_info()}"),
        )()

    def consume_expression(self):
        self.consume_precedence(Precedence.ASSIGNMENT)

    def consume_print_statement(self):
        if self.match(TokenType.SEMICOLON):  # Blank print statement
            self.program.simple_op(OpCode.PRINT_BLANK)
        else:
            self.consume_expression()
            self.consume(
                TokenType.SEMICOLON,
                f"Expected semicolon after statement! {self.prev_info()}",
            )
            self.program.simple_op(OpCode.PRINT)

    def consume_expression_statement(self):
        self.consume_expression()
        self.consume(TokenType.SEMICOLON, f"Expected statement! {self.prev_info()}")
        self.program.simple_op(OpCode.POP)

    def consume_statement(self):
        if self.match(TokenType.PRINT):
            self.consume_print_statement()
        else:
            self.consume_expression_statement()

    def consume_variable(self, message):
        self.consume(TokenType.IDENTIFIER, message)
        return self.get_prev().lexeme

    def consume_variable_declaration(self):
        name = self.consume_variable(f"Expected variable name! {self.prev_info()}")
        self.consume(
            TokenType.EQUAL, f"Expected variable initializer! {self.prev_info()}"
        )
        self.consume_expression()
        self.consume(
            TokenType.SEMICOLON,
            f"Expected semicolon after statement! {self.prev_info()}",
        )
        self.program.define_name(name)

    def consume_variable_reference(self):
        token = self.get_prev()
        if token.token_type != TokenType.IDENTIFIER:
            emit_error(f"Expected variable! {self.prev_info()}")()
        self.program.load_name(token.lexeme)

    def consume_declaration(self):
        if self.match(TokenType.VAL):
            self.consume_variable_declaration()
        else:
            self.consume_statement()


def parse_source(source):

    tokens = tokenize(source)
    if DEBUG:
        print("Tokens:")
        print(" ".join([token.lexeme for token in tokens]))
    parser = Parser(tokens)
    while not parser.match(TokenType.EOF):
        parser.consume_declaration()
    return assemble(parser.flush())
