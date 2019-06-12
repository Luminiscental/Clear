"""
Simple program to interface with the compiler.
Given a module name, it loads the .clr file, compiles it,
and exports the assembled .clr.b.
"""
import sys
import clr.core as clr
import clr.bytecode as bc

DEBUG = False


def main() -> None:
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

    ast = clr.Ast(clr.tokenize_source(source))
    constants, instructions = clr.compile_ast(ast)
    try:
        byte_code = bc.assemble_code(constants, instructions)
    except bc.IndexTooLargeError:
        print("Couldn't assemble; too many variables")
        sys.exit(1)
    except bc.NegativeIndexError:
        print("Couldn't assemble; some variables were unresolved")
        sys.exit(1)
    except bc.StringTooLongError:
        print("Couldn't assemble; string literal was too long")
        sys.exit(1)

    with open(dest_file_name, "wb") as dest_file:
        dest_file.write(byte_code)


if __name__ == "__main__":

    main()
