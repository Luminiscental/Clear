
import struct
from clr.values import OpCode

def first_byte(value):

    return bytes([value])[0]

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

def assemble_any(value, accum):

    accum.append(first_byte(value))

def assemble(code_list):

    raw_bytes = bytearray()
    for code in code_list:
        {
            float: assemble_number,
            str: assemble_string,
            OpCode: assemble_op
        }.get(type(code),
            assemble_any
        )(code, raw_bytes)
    return raw_bytes


