
import struct
from enum import Enum
from clr.tokens import tokenize

class ClrCompileError(Exception):

    pass

class OpCode(Enum):

    STORE_CONST = 0
    NUMBER = 1
    PRINT = 2
    LOAD_CONST = 3
    NEGATE = 4
    ADD = 5
    SUBTRACT = 6
    MULTIPLY = 7
    DIVIDE = 8

    def __int__(self):
        return self.value

    def __str__(self):
        return {
            OpCode.STORE_CONST : 'OP_STORE_CONST',
            OpCode.NUMBER : 'OP_NUMBER',
            OpCode.PRINT : 'OP_PRINT',
            OpCode.LOAD_CONST : 'OP_LOAD_CONST',
            OpCode.NEGATE : 'OP_NEGATE',
            OpCode.ADD : 'OP_ADD',
            OpCode.SUBTRACT : 'OP_SUBTRACT',
            OpCode.MULTIPLY : 'OP_MULTIPLY',
            OpCode.DIVIDE : 'OP_DIVIDE'
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
            code_list.append(OpCode.STORE_CONST)
            code_list.append(OpCode.NUMBER)
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

    def flush(self):
        return self.code_list

def _assemble(code_list):

    raw_bytes = bytearray()
    for code in code_list:
        if isinstance(code, float):
            for byte in struct.pack('d', code):
                raw_bytes.append(byte)
        elif isinstance(code, OpCode):
            byte = bytes([code.value])[0]
            raw_bytes.append(byte)
        else:
            byte = bytes([code])[0]
            raw_bytes.append(byte)
    return raw_bytes

def parse_source(source):

    tokens = tokenize(source)

    constants = Constants()
    program = Program()

    const_a = constants.add(13.2)
    const_b = constants.add(24.7)

    program.load_constant(const_a)
    program.load_constant(const_b)
    program.op_divide()
    program.op_print()

    return _assemble(constants.flush() + program.flush())

