
import struct
from clr.values import OpCode
from clr.errors import emit_error

class Index:

    def __init__(self, index):
        self.value = index

def first_byte(value):

    return bytes([value])[0]

def assemble_index(index, accum):

    accum.append(first_byte(index.value))

def assemble_int(value, accum):

    for byte in struct.pack('i', value):
        accum.append(byte)

def assemble_number(value, accum):

    for byte in struct.pack('d', value):
        accum.append(byte)

def assemble_string(value, accum):

    size = len(value)
    byte_size = first_byte(size)
    accum.append(byte_size)
    for byte in value.encode():
        accum.append(byte)

def assemble_op(op, accum):

    accum.append(first_byte(op.value))

def assemble(code_list):

    raw_bytes = bytearray()
    for code in code_list:
        {
            float: assemble_number,
            str: assemble_string,
            int: assemble_int,
            OpCode: assemble_op,
            Index: assemble_index
        }.get(type(code),
            emit_error(f'Unknown code type to assemble! {type(code)}')
        )(code, raw_bytes)
    return raw_bytes


