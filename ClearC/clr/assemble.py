import struct
from clr.values import OpCode, DEBUG_ASSEMBLE
from clr.errors import emit_error
from clr.constants import ClrInt, ClrUint, ClrNum, ClrStr


def _first_byte(value):

    return bytes([value])[0]


def _assemble_index(index, accum):

    accum.append(_first_byte(index))


def _assemble_int(clrint, accum):

    value = clrint.value
    for byte in struct.pack("i", value):
        accum.append(byte)


def _assemble_uint(clruint, accum):

    value = clruint.value
    for byte in struct.pack("I", value):
        accum.append(byte)


def _assemble_number(clrnum, accum):

    value = clrnum.value
    for byte in struct.pack("d", value):
        accum.append(byte)


def _assemble_string(clrstr, accum):

    value = clrstr.value
    size = len(value)
    byte_size = _first_byte(size)
    accum.append(byte_size)
    for byte in value.encode():
        accum.append(byte)


def _assemble_op(opcode, accum):

    accum.append(_first_byte(opcode.value))


def assembled_size(code_list):
    size = 0
    for code in code_list:
        size += {
            ClrNum: lambda code: 8,
            ClrStr: lambda code: 1 + len(code.value),
            ClrInt: lambda code: 4,
            ClrUint: lambda code: 4,
            OpCode: lambda code: 1,
            int: lambda code: 1,
        }.get(type(code), emit_error(f"Unknown code type to assemble! {type(code)}"))(
            code
        )
    return size


def assemble(code_list):

    if DEBUG_ASSEMBLE:
        print("Byte code to _assemble:")
        for i, code in enumerate(code_list):
            print(f"{i}:{code}")

    raw_bytes = bytearray()
    for code in code_list:
        {
            ClrNum: _assemble_number,
            ClrStr: _assemble_string,
            ClrInt: _assemble_int,
            ClrUint: _assemble_uint,
            OpCode: _assemble_op,
            int: _assemble_index,
        }.get(type(code), emit_error(f"Unknown code type to assemble! {type(code)}"))(
            code, raw_bytes
        )
    return raw_bytes
