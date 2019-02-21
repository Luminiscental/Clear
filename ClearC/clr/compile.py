
import struct
from enum import Enum

class OpCode(Enum):

    STORE_CONST = 0
    NUMBER = 1
    PRINT = 2
    LOAD_CONST = 3

    def __int__(self):
        return self.value

    def __str__(self):
        return {
            OpCode.STORE_CONST : 'OP_STORE_CONST',
            OpCode.NUMBER : 'OP_NUMBER',
            OpCode.PRINT : 'OP_PRINT',
            OpCode.LOAD_CONST : 'OP_LOAD_CONST'
        }[self]

class CompileException(Exception):

    pass

def parse_source(source):

    return list(map(int, [
        OpCode.STORE_CONST,
        OpCode.NUMBER,
        13,
        OpCode.LOAD_CONST,
        0,
        OpCode.PRINT
    ]))

