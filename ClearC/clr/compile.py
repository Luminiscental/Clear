
import struct
from enum import Enum
from clr.tokens import tokenize, TokenType
from clr.errors import ClrCompileError

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
        return {
            OpCode.STORE_CONST : 'OP_STORE_CONST',
            OpCode.NUMBER : 'OP_NUMBER',
            OpCode.STRING : 'OP_STRING',
            OpCode.PRINT : 'OP_PRINT',
            OpCode.LOAD_CONST : 'OP_LOAD_CONST',
            OpCode.NEGATE : 'OP_NEGATE',
            OpCode.ADD : 'OP_ADD',
            OpCode.SUBTRACT : 'OP_SUBTRACT',
            OpCode.MULTIPLY : 'OP_MULTIPLY',
            OpCode.DIVIDE : 'OP_DIVIDE',
            OpCode.RETURN : 'OP_RETURN'
        }.get(self, '<UNKNOWN OP>')

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
            if isinstance(value, float):
                code_list.append(OpCode.STORE_CONST)
                code_list.append(OpCode.NUMBER)
                code_list.append(value)
            elif isinstance(value, str):
                code_list.append(OpCode.STORE_CONST)
                code_list.append(OpCode.STRING)
                code_list.append(value)
            else:
                raise ClrCompileError('Unknown constant value type: {}'
                        .format(value))
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

class Cursor:

    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.constants = Constants()
        self.program = Program()

    def get_current(self):
        return self.tokens[self.index]

    def advance(self):
        self.index += 1

    def consume_expression(self):
        pass

    def consume(self, expected_type, message):
        if self.get_current().token_type == expected_type:
            self.advance()
        else:
            raise ClrCompileError(message)

    def flush(self):
        return self.constants.flush() + self.program.flush()

def parse_source(source):

    tokens = tokenize(source)

    print(' '.join(map(lambda token: token.lexeme, tokens)))

    cursor = Cursor(tokens)
    cursor.consume_expression()
    cursor.consume(TokenType.EOF, "Expect end of expression.")

    return assemble(cursor.flush())

