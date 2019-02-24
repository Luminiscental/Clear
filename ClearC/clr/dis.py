
import struct
from clr.compile import OpCode
from clr.errors import ClrDisassembleError

def disassemble_store(byte, remaining):

    code = OpCode(byte)
    print('{0:16}'.format(str(code)), end='')

    def store_number():
        value = struct.unpack('d', remaining[1:9])[0]
        print('<num {}>'.format(value))
        return 10

    def store_err():
        raise ClrDisassembleError('Unrecognized constant type {}!'.format(
                remaining[0]))

    return {
        OpCode.NUMBER.value : store_number
    }.get(remaining[0], store_err)()

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

def disassembl_err(byte, remaining):

    raise ClrDisassembleError('Unrecognized op code {}!'.format(byte))

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
        OpCode.DIVIDE.value : disassemble_simple
    }.get(byte, disassembl_err)(byte, remaining)

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

