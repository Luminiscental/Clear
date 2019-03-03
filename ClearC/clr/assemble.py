import struct
from clr.values import OpCode
from clr.errors import emit_error
from clr.constants import ClrInt, ClrNum, ClrStr


def first_byte(value):

    return bytes([value])[0]


def assemble_index(index, accum):

    accum.append(first_byte(index))


def assemble_int(clrint, accum):

    value = clrint.value
    for byte in struct.pack("i", value):
        accum.append(byte)


def assemble_number(clrnum, accum):

    value = clrnum.value
    for byte in struct.pack("d", value):
        accum.append(byte)


def assemble_string(clrstr, accum):

    value = clrstr.value
    size = len(value)
    byte_size = first_byte(size)
    accum.append(byte_size)
    for byte in value.encode():
        accum.append(byte)


def assemble_op(opcode, accum):

    accum.append(first_byte(opcode.value))


def assemble(code_list):

    raw_bytes = bytearray()
    for code in code_list:
        {
            ClrNum: assemble_number,
            ClrStr: assemble_string,
            ClrInt: assemble_int,
            OpCode: assemble_op,
            int: assemble_index,
        }.get(type(code), emit_error(f"Unknown code type to assemble! {type(code)}"))(
            code, raw_bytes
        )
    return raw_bytes
