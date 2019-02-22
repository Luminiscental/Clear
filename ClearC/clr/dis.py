
import struct
from clr.compile import OpCode

def _disassemble_store(byte, remaining):

    code = OpCode(byte)
    print('{0:16}'.format(str(code)), end='')

    def store_number():
        value = struct.unpack('d', remaining[1:9])[0]
        print('<num {}>'.format(value))
        return 10

    def store_err():
        return 1

    return {
        OpCode.NUMBER.value : store_number
    }.get(remaining[0], store_err)()

def _disassemble_simple(byte, remaining):

    code = OpCode(byte)
    print(str(code))
    return 1

def _disassemble_constant(byte, remaining):

    code = OpCode(byte)
    value_index = remaining[0]
    print('{0:16}'.format(str(code)), end='')
    print('{}'.format(value_index))
    return 2

def _disassemble_byte(byte, offset, remaining):

    print('{0:04} '.format(offset), end='')

    def unknown_op(byte, remaining):
        print('<UNKNOWN OP>')
        return 1

    return {
        OpCode.STORE_CONST.value : _disassemble_store,
        OpCode.PRINT.value : _disassemble_simple,
        OpCode.LOAD_CONST.value : _disassemble_constant
    }.get(byte, unknown_op)(byte, remaining)

def disassemble(byte_code):

    print('=' * 16)
    offset = 0
    acc = 0
    for byte in byte_code:
        if acc > 0:
            acc -= 1
            continue
        consume = _disassemble_byte(byte, offset,
                                    byte_code[offset + 1:])
        offset += consume
        if consume > 1:
            acc = consume - 1

