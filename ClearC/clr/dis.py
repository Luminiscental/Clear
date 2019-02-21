
from clr.compile import OpCode

def _disassemble_store(code, remaining):

    opcode = OpCode(code)
    print('{0:16}'.format(str(opcode)), end='')

    def store_number():
        print('<num {}>'.format(remaining[1]))
        return 3

    def store_err():
        return 1

    return {
        OpCode.NUMBER.value : store_number
    }.get(remaining[0], store_err)()

def _disassemble_simple(code, remaining):

    opcode = OpCode(code)
    print(str(opcode))
    return 1

def _disassemble_constant(code, remaining):

    opcode = OpCode(code)
    print('{0:16}'.format(str(opcode)), end='')
    print('{}'.format(remaining[0]))
    return 2

def _disassemble_code(code, offset, remaining):

    print('{0:04} '.format(offset), end='')

    def unknown_op(code, remaining):
        print('<UNKNOWN OP>')
        return 1

    return {
        OpCode.STORE_CONST.value : _disassemble_store,
        OpCode.PRINT.value : _disassemble_simple,
        OpCode.LOAD_CONST.value : _disassemble_constant
    }.get(code, unknown_op)(code, remaining)

def disassemble(byte_code):

    print('=' * 16)
    offset = 0
    acc = 0
    for code in byte_code:
        if acc > 0:
            acc -= 1
            continue
        consume = _disassemble_code(code, offset,
                                    byte_code[offset + 1:])
        offset += consume
        if consume > 1:
            acc = consume - 1

