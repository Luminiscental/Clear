import sys
from clr.errors import ClrCompileError
from clr.values import DEBUG
from clr.ast.tree import Ast
from clr.assemble import assemble


def main():

    if len(sys.argv) < 2:
        print("Please provide a file to compile")
        sys.exit(1)
    source_file_name = sys.argv[1] + ".clr"
    dest_file_name = source_file_name + ".b"
    if DEBUG:
        print("src:", source_file_name)
        print("dest:", dest_file_name)
    with open(source_file_name, "r") as source_file:
        source = source_file.read()
    try:
        ast = Ast.from_source(source)
        # TODO: Gen debug symbols
        code = ast.compile()
        if DEBUG:
            print("Assembling:")
        byte_code = assemble(code)
    except ClrCompileError as compile_error:
        # TODO: Synchronize errors on declarations/statements
        print("Could not compile:")
        print(compile_error)
    else:
        print("Compiled successfully")
        with open(dest_file_name, "wb") as dest_file:
            dest_file.write(byte_code)


if __name__ == "__main__":

    main()
