
import struct
from clr.values import OpCode
from clr.errors import emit_error

def disassemble_number(data):

    value = struct.unpack('d', data[0:8])[0]
    print('<num {}>'.format(value))
    return 8

def disassemble_string(data):

    length = data[0]
    byte_string = data[1:length + 1]
    value = byte_string.decode()
    print('<str "{}">'.format(value))
    return 1 + length

def disassemble_store(byte, remaining):

    code = OpCode(byte)
    print('{0:16}'.format(str(code)), end='')

    return 2 + {
        OpCode.NUMBER.value : disassemble_number,
        OpCode.STRING.value : disassemble_string
    }.get(remaining[0], emit_error(
        'Unrecognized constant type {}!'.format(remaining[0]), dis=True
    ))(remaining[1:])

def disassemble_simple(byte, remaining):

    code = OpCode(byte)
    print(str(code))
    return 1

def disassemble_constant(byte, remaining):

    code = OpCode(byte)
    value_index = remaining[0]
    print('{0:16}'.format(str(code)), end='')
    print('{}'.format(value_index))
    return 2

def disassemble_byte(byte, offset, remaining):

    print('{0:04} '.format(offset), end='')
    return {
        OpCode.STORE_CONST.value : disassemble_store,
        OpCode.PRINT.value : disassemble_simple,
        OpCode.LOAD_CONST.value : disassemble_constant,
        OpCode.NEGATE.value : disassemble_simple,
        OpCode.ADD.value : disassemble_simple,
        OpCode.SUBTRACT.value : disassemble_simple,
        OpCode.MULTIPLY.value : disassemble_simple,
        OpCode.DIVIDE.value : disassemble_simple,
        OpCode.RETURN.value : disassemble_simple,
        OpCode.POP.value : disassemble_simple
    }.get(byte, emit_error(
        'Unrecognized op code {}!'.format(byte), dis=True
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

