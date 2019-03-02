
import struct
import sys
from clr.errors import ClrCompileError
from clr.compile import parse_source
from clr.values import debug

def main():

    if len(sys.argv) < 2:
        print('Please provide a file to compile')
        sys.exit(1)

    source_file_name = sys.argv[1] + '.clr'
    dest_file_name = source_file_name + '.b'

    if debug:
        print('src:', source_file_name)
        print('dest:', dest_file_name)

    with open(source_file_name, 'r') as source_file:
        source = source_file.read()

    try:
        if debug:
            print('Source code:')
            print(source)
            print()
            print('Compiling:')
        byte_code = parse_source(source)
    except ClrCompileError as e:
        print('Could not compile:')
        print(e)
    else:
        print('Compiled successfully')
        # TODO: Gen intermediate / AST
        # TODO: Gen debug symbols
        with open(dest_file_name, 'wb') as dest_file:
            dest_file.write(byte_code)

if __name__ == '__main__':

    main()

