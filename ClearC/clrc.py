"""
Simple program to interface with the compiler.
Given a module name, it loads the .clr file, compiles it,
and exports the assembled .clr.b.
"""
import sys
import clr

DEBUG = False


def main():
    """
    The main entry point function, everything is contained here.
    """

    if len(sys.argv) < 2:
        print("Please provide a file to compile")
        sys.exit(1)

    source_file_name = sys.argv[1] + ".clr"
    dest_file_name = source_file_name + ".b"
    if DEBUG:
        print("src:", source_file_name)
        print("dest:", dest_file_name)

    try:
        with open(source_file_name, "r") as source_file:
            source = source_file.read()
    except FileNotFoundError:
        print(f"No file found for {source_file_name}")
        sys.exit(1)

    ast = clr.parse_source(source)
    code = clr.compile_ast(ast)
    byte_code = clr.assemble_code(code)

    with open(dest_file_name, "wb") as dest_file:
        dest_file.write(byte_code)


if __name__ == "__main__":

    main()
