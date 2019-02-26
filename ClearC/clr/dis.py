
import struct
from clr.values import OpCode
from clr.errors import emit_error

def disassemble_bool(data):

    value = bool(data[0])
    print(f'<bool {value}>')
    return 1

def disassemble_number(data):

    value = struct.unpack('d', data[0:8])[0]
    print(f'<num {value}>')
    return 8

def disassemble_string(data):

    length = data[0]
    byte_string = data[1:length + 1]
    value = byte_string.decode()
    print(f'<str "{value}">')
    return 1 + length

def disassemble_store(byte, remaining):

    code = OpCode(byte)
    print(f'{str(code):16}', end='')

    return 2 + {
        OpCode.NUMBER.value : disassemble_number,
        OpCode.STRING.value : disassemble_string
    }.get(remaining[0], emit_error(
        f'Unrecognized constant type {remaining[0]}!', dis=True
    ))(remaining[1:])

def disassemble_simple(byte, remaining):

    code = OpCode(byte)
    print(str(code))
    return 1

def disassemble_constant(byte, remaining):

    code = OpCode(byte)
    value_index = remaining[0]
    print(f'{str(code):16}', end='')
    print(f'{value_index}')
    return 2

def disassemble_define(byte, remaining):

    code = OpCode(byte)
    print(f'{str(code):16}', end='')
    return 1 + disassemble_string(remaining)

def disassemble_byte(byte, offset, remaining):

    print(f'{offset:04} ', end='')
    return {
        OpCode.STORE_CONST.value: disassemble_store,
        OpCode.PRINT.value: disassemble_simple,
        OpCode.LOAD_CONST.value: disassemble_constant,
        OpCode.NEGATE.value: disassemble_simple,
        OpCode.ADD.value: disassemble_simple,
        OpCode.SUBTRACT.value: disassemble_simple,
        OpCode.MULTIPLY.value: disassemble_simple,
        OpCode.DIVIDE.value: disassemble_simple,
        OpCode.RETURN.value: disassemble_simple,
        OpCode.POP.value: disassemble_simple,
        OpCode.DEFINE.value: disassemble_define,
        OpCode.TRUE.value: disassemble_simple,
        OpCode.FALSE.value: disassemble_simple,
        OpCode.NOT.value: disassemble_simple,
        OpCode.EQUAL.value: disassemble_simple,
        OpCode.NEQUAL.value: disassemble_simple,
        OpCode.LESS.value: disassemble_simple,
        OpCode.NLESS.value: disassemble_simple,
        OpCode.GREATER.value: disassemble_simple,
        OpCode.NGREATER.value: disassemble_simple
    }.get(byte, emit_error(
        f'Unrecognized op code {byte}!', dis=True
    ))(byte, remaining)

def disassemble(byte_code):

    print('=' * 16)
    offset = 0
    acc = 0
    for byte in byte_code:
        if acc > 0:
            acc -= 1
            continue
        consume = disassemble_byte(byte, offset,
                                    byte_code[offset + 1:])
        offset += consume
        if consume > 1:
            acc = consume - 1

