
import struct
from enum import Enum
from clr.tokens import tokenize, TokenType
from clr.errors import ClrCompileError

def emit_error(message):

    def emission():
        raise ClrCompileError(message)
    return emission

class OpCode(Enum):

    STORE_CONST = 0
    NUMBER = 1
    STRING = 2
    PRINT = 3
    LOAD_CONST = 4
    NEGATE = 5
    ADD = 6
    SUBTRACT = 7
    MULTIPLY = 8
    DIVIDE = 9
    RETURN = 10

    def __int__(self):
        return self.value

    def __str__(self):
        return 'OP_' + self.name

class Precedence(Enum):

    NONE = 0
    ASSIGNMENT = 1
    OR = 2
    AND = 3
    EQUALITY = 4
    COMPARISON = 5
    TERM = 6
    FACTOR = 7
    UNARY = 8
    CALL = 9
    PRIMARY = 10

class Constants:

    def __init__(self):
        self.values = []
        self.count = 0

    def add(self, value):
        if value in self.values:
            return self.values.index(value)
        else:
            self.values.append(value)
            self.count += 1
            return self.count - 1

    def flush(self):
        code_list = []
        for value in self.values:
            code_list.append(OpCode.STORE_CONST)
            value_type = type(value)

            op_type = {
                float: lambda: OpCode.NUMBER,
                str: lambda: OpCode.STRING
            }.get(value_type, emit_error('Unknown constant value type: {}'
                        .format(value_type)))()

            code_list.append(op_type)
            code_list.append(value)
        return code_list

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

    def flush(self):
        return self.code_list

def assemble(code_list):

    raw_bytes = bytearray()
    for code in code_list:
        if isinstance(code, float):
            for byte in struct.pack('d', code):
                raw_bytes.append(byte)
        elif isinstance(code, str):
            size = len(code)
            byte_size = bytes([size])[0]
            raw_bytes.append(byte_size)
            for byte in code.encode():
                raw_bytes.append(byte)
        elif isinstance(code, OpCode):
            byte = bytes([code.value])[0]
            raw_bytes.append(byte)
        else:
            byte = bytes([code])[0]
            raw_bytes.append(byte)
    return raw_bytes

class ParseRule:

    def __init__(self, infix=None, prefix=None, precedence=None):
        self.infix = infix if infix else emit_error('Expected expression')
        self.prefix = prefix if prefix else emit_error('Expected expression')
        self.precedence = precedence if precedence else Precedence.NONE

class Cursor:

    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.constants = Constants()
        self.program = Program()

    def get_current(self):
        return self.tokens[self.index]

    def get_last(self):
        return self.tokens[self.index - 1]

    def advance(self):
        self.index += 1

    def get_rule(self, token):
        return {
            TokenType.LEFT_PAREN : ParseRule(
                prefix=self.finish_grouping,
                precedence=Precedence.CALL
            ),
            TokenType.MINUS : ParseRule(
                prefix=self.finish_unary,
                infix=self.finish_binary,
                precedence=Precedence.TERM
            ),
            TokenType.PLUS : ParseRule(
                infix=self.finish_binary,
                precedence=Precedence.TERM
            ),
            TokenType.SLASH : ParseRule(
                infix=self.finish_binary,
                precedence=Precedence.FACTOR
            ),
            TokenType.STAR : ParseRule(
                infix=self.finish_binary,
                precedence=Precedence.FACTOR
            ),
            TokenType.NUMBER : ParseRule(
                prefix=self.consume_number
            ),
            TokenType.AND : ParseRule(
                precedence=Precedence.AND
            ),
            TokenType.OR : ParseRule(
                precedence=Precedence.OR
            )
        }.get(token.token_type, ParseRule()) 

    def consume_number(self):
        token = self.get_last()
        if token.token_type != TokenType.NUMBER:
            emit_error('Expected number token!')()
        const_index = self.constants.add(float(token.lexeme))
        self.program.load_constant(const_index)

    def consume_precedence(self, precedence):
        self.advance()
        self.get_rule(self.get_last()).prefix()
        while precedence.value <= self.get_rule(self.get_current()).precedence.value:
            self.advance()
            self.get_rule(self.get_last()).infix()

    def finish_grouping(self):
        self.consume_expression()
        self.consume(TokenType.RIGHT_PAREN, 'Expect ) after expression')

    def finish_unary(self):
        op_token = self.get_last()
        self.consume_precedence(Precedence.UNARY)
        {
            TokenType.MINUS : self.program.op_negate
        }.get(op_token.token_type, emit_error('Expected unary operator'))()

    def finish_binary(self):
        op_token = self.get_last()
        rule = self.get_rule(op_token)
        self.consume_precedence(rule.precedence)
        {
            TokenType.PLUS : self.program.op_add,
            TokenType.MINUS : self.program.op_subtract,
            TokenType.STAR : self.program.op_multiply,
            TokenType.SLASH : self.program.op_divide
        }.get(op_token.token_type, emit_error('Expected binary operator'))()

    def consume_expression(self):
        self.consume_precedence(Precedence.ASSIGNMENT)

    def consume(self, expected_type, message):
        if self.get_current().token_type == expected_type:
            self.advance()
        else:
            emit_error(message)()

    def flush(self):
        self.program.op_return()
        return self.constants.flush() + self.program.flush()

def parse_source(source):

    tokens = tokenize(source)

    print(' '.join(map(lambda token: token.lexeme, tokens)))

    cursor = Cursor(tokens)
    cursor.consume_expression()
    cursor.consume(TokenType.EOF, "Expect end of expression.")

    return assemble(cursor.flush())

