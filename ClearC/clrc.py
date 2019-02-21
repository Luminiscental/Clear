
import sys
from enum import Enum

class CompileException(Exception):
    pass

class OpCode(Enum):
    PRINT = 0
    CONSTANT = 1

    def __int__(self):
        return self.value

    def __str__(self):
        return { OpCode.PRINT    : 'OP_PRINT',
                 OpCode.CONSTANT : 'OP_CONSTANT' }[self]

def parse_source(source):
    return [ OpCode.CONSTANT,
             13,
             OpCode.PRINT ]

def disassemble_simple(op, remaining):
    print(str(op))
    return 1

def disassemble_constant(op, remaining):
    print('{0:16}'.format(str(op)), end='')
    print(remaining[0])
    return 2

def disassemble_byte(byte, offset, remaining):
    def unknown_op(op, remaining):
        print('<UNKNOWN OP>')
        return 1

    print('{0:04} '.format(offset), end='')
    return { OpCode.PRINT    : disassemble_simple,
             OpCode.CONSTANT : disassemble_constant }.get(byte, unknown_op) (byte, remaining)

def disassemble(byte_code):
    print('========')
    offset = 0
    acc = 0
    for byte in byte_code:
        if acc > 0:
            acc = acc - 1
            continue

        consume = disassemble_byte(byte, offset, byte_code[offset + 1:])
        offset = offset + consume
        acc = consume - 1

def main():
    if len(sys.argv) < 2:
        print('Please provide a file to compile')
        sys.exit(1)

    source_file_name = sys.argv[1]
    dest_file_name = source_file_name + '.b'

    with open(source_file_name, 'r') as source_file:
        source = source_file.read()
        try:
            byte_code = parse_source(source)
            disassemble(byte_code)
        except CompileException as e:
            print('Could not compile:')
            print(e)
        else:
            with open(dest_file_name, 'wb') as dest_file:
                dest_file.write(bytes(map(int, byte_code)))

if __name__ == '__main__':
    main()

