
from enum import Enum
import re
import sys

name_re = "[a-zA-Z][a-zA-Z0-9]*"

# 0: val/var, 1: name, 2: type or None, 3: value or None
variable_re_capturing = "(val|var)\s+(" + name_re + ")\s*(?::\s*(" + name_re + "))?(?:(?:\s*=\s*)(.*))?"
variable_re = "(?:val|var)\s+(?:" + name_re + ")\s*(?::\s*(?:" + name_re + "))?(?:(?:\s*=\s*)(?:.*))?"

# 0: condition
if_re_capturing = "if\s*\((.*)\)"

# 0: init, 1: condition, 2: increment
for_re_capturing = "for\s*\((.*)\s*;\s*(.*)\s*;\s*(.*)\)"

# 0: name, 1: params, 2: return type or None
func_re_capturing = "func\s+(" + name_re + ")\s*\(((?:(?:" + variable_re + ")(?:\s*,\s*" + variable_re + ")*)?)\)\s*(?::\s*(" + name_re + "))?"

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

# TODO: else, else if, e.t.c.
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
    STATEMENT = 1

class StatementType(Enum):

    NONE = 0
    VARIABLE = 1
    IF = 2
    FOR = 3
    FUNCTION = 4

class CrystalVariable:

    def __init__(self, mutable, name, value_type = None, value_init = None):

        self.mutable = mutable
        self.name = name
        self.type = value_type
        self.value = value_init

        if not self.type and not self.value:

            raise CompileException("Cannot declare implicitly typed variable without a value: \"" + declaration + "\"")

    @staticmethod
    def parse(declaration):

        match_variable = re.search(variable_re_capturing, declaration)

        if not match_variable:

            # this should never happen
            raise CompileException("Expression \"" + declaration + "\" does not declare a variable")

        tokens = match_variable.groups()
        return CrystalVariable(tokens[0] == "var", tokens[1], tokens[2], tokens[3])

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

class CrystalIf:

    def __init__(self, condition):

        self.condition = condition

    def __str__(self):

        return "if(" + self.condition + ")"

class CrystalFor:

    def __init__(self, init, condition, increment):

        self.init = CrystalStatement(init)
        self.condition = condition
        self.increment = CrystalStatement(increment)

    def __str__(self):

        return "for(" + str(self.init) + self.condition + ";" + str(self.increment)[:-1] + ")"

class CrystalFunction:

    def __init__(self, name, param_string, return_string):

        self.name = name
        self.params = [CrystalVariable.parse(param) for param in param_string.split(",") if param]
        self.return_type = return_string

        if name == "main":

            if self.return_type:

                raise CompileException("Main function does not return but was declared as returning " + self.return_type)

            self.return_type = "int"

    def __str__(self):

        r = self.return_type if self.return_type else "void"
        return r + " " +  self.name + "(" + ",".join([str(p) for p in self.params]) + ")"

class CrystalStatement:

    def __init__(self, line):

        match_variable = re.search(variable_re_capturing, line)
        match_if = re.search(if_re_capturing, line)
        match_for = re.search(for_re_capturing, line)
        match_func = re.search(func_re_capturing, line)

        if match_func:

            tokens = match_func.groups()

            self.statement_type = StatementType.FUNCTION
            self.as_func = CrystalFunction(tokens[0], tokens[1], tokens[2])

        elif match_for:

            tokens = match_for.groups()
            self.statement_type = StatementType.FOR
            self.as_for = CrystalFor(tokens[0], tokens[1], tokens[2])

        elif match_if:

            tokens = match_if.groups()
            self.statement_type = StatementType.IF
            self.as_if = CrystalIf(tokens[0])

        elif match_variable:

            tokens = match_variable.groups()
            self.statement_type = StatementType.VARIABLE
            self.as_variable = CrystalVariable(tokens[0] == "var", tokens[1], tokens[2], tokens[3])

        else:

            self.statement_type = StatementType.NONE
            self.as_string = line

    def __str__(self):

        if self.statement_type == StatementType.VARIABLE:

            return str(self.as_variable) + ";"

        elif self.statement_type == StatementType.IF:

            return str(self.as_if)

        elif self.statement_type == StatementType.FOR:

            return str(self.as_for)

        elif self.statement_type == StatementType.FUNCTION:

            return str(self.as_func)

        elif self.statement_type == StatementType.NONE:

            return self.as_string + ";"

class Scope:

    def __init__(self, header = "", parent = None, root = False):

        self.root = root
        self.parent = parent
        self.header = header
        self.children = []

        if header:

            self.scope_type = ScopeType.STATEMENT
            self.as_statement = CrystalStatement(header)

            if self.as_statement.statement_type == StatementType.NONE:

                raise CompileException("Unknown scope type for header: \"" + header + "\"")

            elif self.as_statement.statement_type == StatementType.VARIABLE:

                raise CompileException("Variable declarations do not open a scope: \"" + header + "\"")

        else:

            self.scope_type = ScopeType.DEFAULT

    def add_child(self, child):

        child.parent = self
        self.children.append(child)

    def __str__(self):

        result = ""

        if self.scope_type == ScopeType.STATEMENT:

            result = result + str(self.as_statement)

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

