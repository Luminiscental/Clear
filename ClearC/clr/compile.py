
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

    return _assemble([
        OpCode.STORE_CONST,
        OpCode.NUMBER,
        13.2,
        OpCode.LOAD_CONST,
        0,
        OpCode.PRINT
    ])

