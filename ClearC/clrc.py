
import struct
import sys
from clr.dis import disassemble, ClrDisassembleError
from clr.compile import parse_source, ClrCompileError, OpCode

debug = True

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
        if debug:
            try:
                disassemble(byte_code)
            except ClrDisassembleError as e:
                print('Could not disassemble:')
                print(e)
    except ClrCompileError as e:
        print('Could not compile:')
        print(e)
    else:
        print()
        print(dest_file_name)
        with open(dest_file_name, 'wb') as dest_file:
            dest_file.write(byte_code)

if __name__ == '__main__':

    main()

