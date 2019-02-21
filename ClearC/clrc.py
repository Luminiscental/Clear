
import struct
import sys
from clr.dis import disassemble
from clr.compile import parse_source, CompileException

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
                disassemble(byte_code)
        except CompileException as e:
            print('Could not compile:')
            print(e)
        else:
            with open(dest_file_name, 'wb') as dest_file:
                raw_bytes = bytearray()
                for code in byte_code:
                    byte = bytes([code])[0]
                    print(byte)
                    raw_bytes.append(byte)
                print(raw_bytes)
                print(dest_file_name)
                dest_file.write(raw_bytes)

if __name__ == '__main__':

    main()

