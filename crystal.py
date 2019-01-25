
from enum import Enum
import re
import sys

name_re = "[a-zA-Z][a-zA-Z0-9]*"

cy_header = """
"""

cpp_header = """#include <iostream>
void print() {
    std::cout << std::endl;
}
template <typename T, typename ...Arguments>
void print(T first, Arguments... args) {
    std::cout << first;
    print(args...);
}
"""

# TODO: import / module stuff
# TODO: namespacing
# TODO: classes
# TODO: other for loop forms, switch case
# TODO: templates
# TODO: varargs

class CompileException(Exception):
    pass

class ScopeType(Enum):

    DEFAULT = 0
    FUNCTION = 1
    IF = 2
    FOR = 3

class StatementType(Enum):

    NONE = 0
    VARIABLE = 1

class CrystalVariable:

    def __init__(self, declaration):

        tokens = re.search("(val|var)\s+(" + name_re + ")\s*(?::\s*(" + name_re + "))?(?:(?:\s*=\s*)(.*))?", declaration).groups()

        self.mutable = tokens[0] == "var"
        self.name = tokens[1]
        self.type = tokens[2]
        self.value = tokens[3]

        if not self.type and not self.value:

            raise CompileException("Cannot declare implicitly typed variable without a value: \"" + declaration + "\"")

    def __str__(self):

        result = ""

        if not self.mutable:

            result = result + "const"
            result = result + " "

        result = result + self.type if self.type else "auto"
        result = result + " "

        result = result + self.name
        result = result + " "

        if self.value:

            result = result + "=" + self.value
            result = result + " "

        return result

class CrystalStatement:

    def __init__(self, line):

        if line.startswith("val") or line.startswith("var"):

            self.statement_type = StatementType.VARIABLE
            self.as_variable = CrystalVariable(line)

        else:

            self.statement_type = StatementType.NONE
            self.as_string = line

    def __str__(self):

        if self.statement_type == StatementType.VARIABLE:

            return str(self.as_variable) + ";"

        elif self.statement_type == StatementType.NONE:

            return self.as_string + ";"

class CrystalFunction:

    def __init__(self, header):

        tokens = re.search("func\s+(" + name_re + ")\s*\((.*)\)\s*(?::\s*(.*))?", header).groups()
        self.name = tokens[0]
        self.params = [CrystalVariable(declaration) for declaration in tokens[1].split(",") if declaration]
        self.return_type = tokens[2]

        if self.name == "main":

            self.return_type = "int"

    def __str__(self):

        r = self.return_type if self.return_type else "void"
        return r + " " +  self.name + "(" + ",".join([str(p) for p in self.params]) + ")"

class CrystalIf:

    def __init__(self, header):

        tokens = re.search("if\s*\((.*)\)", header).groups()
        self.condition = tokens[0]

    def __str__(self):

        return "if(" + self.condition + ")"

class CrystalFor:

    def __init__(self, header):

        tokens = re.search("for\s*\((.*)\s*;\s*(.*)\s*;\s*(.*)\)", header).groups()
        self.init = CrystalStatement(tokens[0])
        self.condition = tokens[1]
        self.increment = CrystalStatement(tokens[2])

    def __str__(self):

        return "for(" + str(self.init) + self.condition + ";" + str(self.increment)[:-1] + ")"

class Scope:

    def __init__(self, header = "", parent = None, root = False):

        self.root = root
        self.parent = parent
        self.header = header
        self.children = []

        if header:

            if header.startswith("func"):

                self.scope_type = ScopeType.FUNCTION
                self.as_func = CrystalFunction(header)

            elif header.startswith("if"):

                self.scope_type = ScopeType.IF
                self.as_if = CrystalIf(header)

            elif header.startswith("for"):

                self.scope_type = ScopeType.FOR
                self.as_for = CrystalFor(header)

            else:

                raise CompileException("Unknown scope type for header: \"", header, "\"")

        else:

            self.scope_type = ScopeType.DEFAULT

    def add_child(self, child):

        self.children.append(child)

    def __str__(self):

        result = ""

        if self.scope_type == ScopeType.FUNCTION:

            result = result + str(self.as_func)

        elif self.scope_type == ScopeType.IF:

            result = result + str(self.as_if)

        elif self.scope_type == ScopeType.FOR:

            result = result + str(self.as_for)

        if not self.root:

            result = result + "{\n"

        for child in self.children:

            result = result + str(child) + "\n"

        if not self.root:

            result = result + "}"

        return result

class ScopeTree:

    def __init__(self):

        self.root = Scope(root = True)
        self.current = self.root

    def push_scope(self, scope):

        self.current.add_child(scope)
        scope.parent = self.current
        self.current = scope

    def pop_scope(self):

        self.current = self.current.parent

    def add_statement(self, statement):

        self.current.add_child(statement)

    def __str__(self):

        return str(self.root)

def parse_source(source):

    result = ScopeTree()

    for line in source.splitlines():

        tokens = line.split()
        header = ""

        for token in tokens:

            if token == "{":

                result.push_scope(Scope(header))
                header = ""

            elif token == "}":

                result.pop_scope()

            else:

                header = header + token + " "

        if header:

            result.add_statement(CrystalStatement(header))

    return result

def main():

    if len(sys.argv) < 2:

        print("Please provide a file to transpile")
        sys.exit(1)

    source_file_name = sys.argv[1]
    dest_file_name = sys.argv[2] if len(sys.argv) > 2 else source_file_name.replace(".cy", ".cpp")

    source_file = open(source_file_name, "r")
    source = source_file.read()
    source_file.close()

    try:

        ast = parse_source(cy_header + source)

        dest_file = open(dest_file_name, "w")
        dest_file.write(cpp_header + str(ast))
        dest_file.close()

    except CompileException as e:

        print("Could not compile:")
        print(e)

if __name__ == "__main__":

    main()

