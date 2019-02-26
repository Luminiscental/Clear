
from clr.tokens import tokenize, TokenType, token_info
from clr.errors import emit_error
from clr.assemble import assemble
from clr.values import OpCode, Precedence, pratt_table

class Constants:

    def __init__(self):
        self.values = []
        self.count = 0
        self.code_list = []

    def add(self, value):
        if value in self.values:
            return self.values.index(value)
        else:
            self.values.append(value)
            self.count += 1
            return self.count - 1

    def store(self, op_type, value):
        self.code_list.append(OpCode.STORE_CONST)
        self.code_list.append(op_type)
        self.code_list.append(value)

    def flush(self):
        for value in self.values:
            value_type = type(value)
            op_type = {
                float: lambda: OpCode.NUMBER,
                str: lambda: OpCode.STRING
            }.get(value_type, emit_error(
                'Unknown constant value type: {}'.format(value_type))
            )()
            self.store(op_type, value)
        return self.code_list

class Program:

    def __init__(self):
        self.code_list = []

    def load_constant(self, constant):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def op_print(self):
        self.code_list.append(OpCode.PRINT)

    def op_negate(self):
        self.code_list.append(OpCode.NEGATE)

    def op_add(self):
        self.code_list.append(OpCode.ADD)

    def op_subtract(self):
        self.code_list.append(OpCode.SUBTRACT)

    def op_multiply(self):
        self.code_list.append(OpCode.MULTIPLY)

    def op_divide(self):
        self.code_list.append(OpCode.DIVIDE)

    def op_return(self):
        self.code_list.append(OpCode.RETURN)

    def op_pop(self):
        self.code_list.append(OpCode.POP)

    def op_define(self, name):
        self.code_list.append(OpCode.DEFINE)
        self.code_list.append(name)

    def flush(self):
        return self.code_list

class Cursor:

    def __init__(self, tokens, constants, program):
        self.index = 0
        self.tokens = tokens
        self.constants = constants
        self.program = program

    def get_current(self):
        return self.tokens[self.index]

    def get_prev(self):
        return self.tokens[self.index - 1]

    def current_info(self):
        return token_info(self.get_current())

    def advance(self):
        self.index += 1

    def check(self, token_type):
        return self.get_current().token_type == token_type

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        else:
            self.advance()
            return True

    def consume(self, expected_type, message):
        if not self.match(expected_type):
            emit_error(message)()

    def flush(self):
        self.program.op_return()
        return self.constants.flush() + self.program.flush()

class Parser(Cursor):

    def __init__(self, tokens):
        super().__init__(tokens, Constants(), Program())

    def get_rule(self, token):
        err = emit_error('Expected expression! {}'.format(token_info(token)))
        rule = pratt_table(self)[token.token_type]
        rule.fill(err)
        return rule

    def consume_number(self):
        token = self.get_prev()
        if token.token_type != TokenType.NUMBER:
            emit_error(
                'Expected number token! {}'.format(self.current_info()))()
        const_index = self.constants.add(float(token.lexeme))
        self.program.load_constant(const_index)

    def consume_string(self):
        token = self.get_prev()
        if token.token_type != TokenType.STRING:
            emit_error(
                'Expected string token! {}'.format(self.current_info()))()
        const_index = self.constants.add(token.lexeme[1:-1])
        self.program.load_constant(const_index)

    def consume_precedence(self, precedence):
        self.advance()
        self.get_rule(self.get_prev()).prefix()
        while precedence.value <= self.get_rule(
                self.get_current()).precedence.value:
            self.advance()
            self.get_rule(self.get_prev()).infix()

    def finish_grouping(self):
        self.consume_expression()
        self.consume(TokenType.RIGHT_PAREN,
            'Expect ) after expression! {}'.format(self.current_info()))

    def finish_unary(self):
        op_token = self.get_prev()
        self.consume_precedence(Precedence.UNARY)
        {
            TokenType.MINUS : self.program.op_negate
        }.get(op_token.token_type, emit_error(
            'Expected unary operator! {}'.format(self.current_info())
        ))()

    def finish_binary(self):
        op_token = self.get_prev()
        rule = self.get_rule(op_token)
        self.consume_precedence(rule.precedence)
        {
            TokenType.PLUS : self.program.op_add,
            TokenType.MINUS : self.program.op_subtract,
            TokenType.STAR : self.program.op_multiply,
            TokenType.SLASH : self.program.op_divide
        }.get(op_token.token_type, emit_error(
            'Expected binary operator! {}'.format(self.current_info())
        ))()

    def consume_expression(self):
        self.consume_precedence(Precedence.ASSIGNMENT)

    def consume_print_statement(self):
        self.consume_expression()
        self.consume(TokenType.SEMICOLON,
            'Expect semicolon after print statement! {}'.format(
                self.current_info()))
        self.program.op_print()

    def consume_expression_statement(self):
        self.consume_expression()
        self.consume(TokenType.SEMICOLON,
            'Expected statement! {}'.format(self.current_info()))
        self.program.op_pop()

    def consume_statement(self):
        if self.match(TokenType.PRINT):
            self.consume_print_statement()
        else:
            self.consume_expression_statement()

    def consume_variable(self, message):
        self.consume(TokenType.IDENTIFIER, message)
        return self.get_prev().lexeme

    def consume_variable_declaration(self):
        name = self.consume_variable('Expect variable name')
        self.consume(TokenType.EQUAL, 'Expect variable initializer')
        self.consume_expression()
        self.consume(TokenType.SEMICOLON,
                'Expect semicolon to end statement! {}'.format(
                    self.current_info()))
        self.program.op_define(name)

    def consume_declaration(self):
        if self.match(TokenType.VAR) or self.match(TokenType.VAL):
            self.consume_variable_declaration()
        else:
            self.consume_statement()

def parse_source(source):

    tokens = tokenize(source)

    print(' '.join(map(lambda token: token.lexeme, tokens)))

    parser = Parser(tokens)
    while not parser.match(TokenType.EOF):
        parser.consume_declaration()

    return assemble(parser.flush())

