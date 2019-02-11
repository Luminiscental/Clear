
from enum import Enum
import re
import sys

closers = { "{": "}", "(": ")", "[": "]" }

name_re = "[a-zA-Z][a-zA-Z0-9]*"

cy_header = """
"""

cpp_header = """// cpp_header:

#include <iostream>
void print() {
    std::cout << std::endl;
}
template <typename T, typename ...Arguments>
void print(T first, Arguments... args) {
    std::cout << first;
    print(args...);
}

"""

def indent_block(block):

    return "".join(["\t" + line + "\n" for line in block.splitlines()])

class CompileException(Exception):

    pass

# TODO: __str__

class CrystalExpression:

    def __init__(self, string):

        # TODO

        pass

    def __str__(self):

        return "Expression"

class CrystalStatement:

    # TODO

    pass

'''
self.mutable : True if var, False if val
self.name : string containing the name of this variable
self.type : string containing the type of this variable
self.value : CrystalExpression for the value this variable is initialized with
'''

class CrystalVariable:

    def __init__(self, declaration, parameter = False):

        tokens = [token for token in re.split("\s+|(:)|(=)", declaration) if token]

        if len(tokens) < 2:

            raise CompileException("variables need a mutability signifier and a name, found only " + str(len(tokens)) + " tokens")

        if tokens[0] != "val" and tokens[0] != "var":

            raise CompileException("Variables must be declared with either val or var")

        self.mutable = tokens[0] == "var"
        self.name = tokens[1]
        self.type = None
        self.value = None

        def check_value(check_tokens):

            if check_tokens[0] == "=":

                if len(check_tokens) < 2:

                    raise CompileException("Value specification indicated but not provided")

                self.value = CrystalExpression(check_tokens[1])

                if len(check_tokens) > 2:

                    raise CompileException("Unexpected tokens in variable declaration: " + str(check_tokens[2:]))

            else:

                raise CompileException("Unexpected token " + check_tokens[0])

        if len(tokens) > 2:
            
            extra_tokens = tokens[2:]

            if extra_tokens[0] == ":":

                if len(extra_tokens) < 2:

                    raise CompileException("Type specification indicated but not provided")

                self.type = extra_tokens[1]

                if len(extra_tokens) > 2:

                    check_value(extra_tokens[2:])

            else:
                
                check_value(extra_tokens)

    def __str__(self):

        return ("mutable " if self.mutable else "") + "variable: " + self.name + ": " + (self.type if self.type else "auto") + (" = " + str(self.value) if self.value else "")

'''
self.statements : list of CrystalStatement instances for all the code executed in this block
self.return_statement : the final statement that returns a value
'''

class CrystalReturn:

    def __init__(self, body_node):

        self.statements = []
        self.return_statement = None

        if body_node.type != "{":

            raise CompileException("Function body enclosed in wrong block type")

        return_found = False

        for child in body_node.children:

            if return_found:

                raise CompileException("Statements found after return statement")

#            statement = CrystalStatement(child)
#
#            if statement.returns:
#
#                self.return_statement = statement
#                return_found = True
#
#            else:
#
#                self.statements.append(statement)

    def __str__(self):

        return "Function body"

'''
self.params : list of CrystalVariable instances for each input variable
'''

class CrystalParams:

    def __init__(self, param_node):

        if param_node.type != "(":

            raise CompileException("Function parameters enclosed in wrong block type")

        if len(param_node.children) != 1:

            raise CompileException("Function parameters must be a list of variables, got " + str(len(param_node.children)) + " children instead")

        param_string = param_node.children[0]
        self.params = [CrystalVariable(param, parameter = True) for param in param_string.split(",") if param]

    def __str__(self):

        return "(" + ",".join([str(param) for param in self.params]) + ")"

'''
self.name : name of the function as a string
self.params : a CrystalParams instance for storing the function signature
self.ret : the return type as a string
self.body : a CrystalReturn instance for storing the returning {-scope of the function body
'''

class CrystalFunction:

    def __init__(self, name, params, ret, body):

        self.name = name
        self.params = CrystalParams(params)

        if ret.strip():

            # TODO: Abstract out type annotations
            ret_match = re.search("\s*:\s*(" + name_re + ")", ret)

            if not ret_match:

                raise CompileException("Invalid return expression for function: \"" + ret + "\"")

            self.ret = ret_match.groups()[0]

        else:

            self.ret = None

        self.body = CrystalReturn(body)

    def __str__(self):

        return "function: " + self.name + str(self.params) + ":" + (self.ret if self.ret else "void") + "\n" + str(self.body)

'''
header: the line header to attempt to parse as a statement
others: children of scope following header

return: parsed statement, number of children after the header composing the statement or None, 0 if no statement parsed
'''
def parse_block(header, others):

    if isinstance(header, CrystalNode):

        return None, 0

    func_match = re.search("func\s+(" + name_re + ")", header)

    if func_match:

        name = func_match.groups()[0]
        params = others[0]

        if not params or not isinstance(params, CrystalNode):

            raise CompileException("Function declaration without param block")

        if len(others) < 2 or not others[1]:

            raise CompileException("Function declaration requires body, only children after name: " + str(others))

        ret = None
        body_index = 1

        if not isinstance(others[1], CrystalNode):

            ret = others[1]
            body_index = 2

        body = others[body_index]

        if not isinstance(body, CrystalNode):

            raise CompileException("Function declaration requires a body, no node followed name and params.")

        return CrystalFunction(name, params, ret, body), body_index + 2

    return None, 0

'''
self.type : either "{", "(", or "[" - the type of block this is
self.children : a list of strings and CrystalNode instances that are contained in this block
self.parent : CrystalNode that self is contained in, or None for the root node
'''

class CrystalNode:

    def __init__(self, opener = "{"):

        self.type = opener
        self.children = []
        self.parent = None

    def __str__(self):

        return self.type + "\n" + "\n".join([indent_block(str(child)) for child in self.children]) + closers[self.type]

    def add_line(self, line):

        self.children.append(line)

    def add_child(self, opener):

        node = CrystalNode(opener)
        node.parent = self
        self.children.append(node)

    def collapse(self):

        for child in self.children:

            if isinstance(child, CrystalNode):

                child.collapse()

        new_children = []
        num_children = len(self.children)

        collapsed_child_indices = []

        for i in range(0, num_children):

            if i in collapsed_child_indices:

                continue

            child = self.children[i]
            after_child = self.children[i + 1:]

            as_block, consumed = parse_block(child, after_child)

            if as_block:

                collapsed_child_indices.extend(range(i, i + consumed))
                new_children.append(as_block)

            else:

                new_children.append(child)

        self.children = new_children

'''
self.root : CrystalNode instance for the root scope
self.current : CrystalNode instance that is currently having children appended
'''

class CrystalAst:

    def __init__(self):

        self.root = CrystalNode()
        self.current = self.root

    def __str__(self):

        return str(self.root)

    def add_line(self, line):

        self.current.add_line(line)

    def push_block(self, opener):

        self.current.add_child(opener)
        self.current = self.current.children[-1]

    def pop_block(self):

        self.current = self.current.parent

    def parse_line(self, line):

        acc = ""

        for c in line:

            # TODO: Strings

            if c == "(" or c == "{" or c == "[":

                self.add_line(acc)
                acc = ""
                self.push_block(c)

            elif c == ")" or c == "}" or c == "]":

                self.add_line(acc)
                acc = ""
                self.pop_block()

            else:

                acc = acc + c

    def collapse(self):

        self.root.collapse()

def parse_source(source):

    ast = CrystalAst()

    for line in source.splitlines():

        ast.parse_line(line)

    ast.collapse()

    return ast

def main():

    if len(sys.argv) < 2:

        print("Please provide a file to transpile")
        sys.exit(1)

    source_file_name = sys.argv[1]

    if len(sys.argv) > 2:

        dest_file_name = sys.argv[2]

    elif source_file_name[-3:] == ".cr":

        dest_file_name = source_file_name.replace(".cr", ".cpp")

    else:

        dest_file_name = source_file_name + ".cpp"

    with open(source_file_name, "r") as source_file:

        source = source_file.read()

        try:

            ast = parse_source(cy_header + source)

            with open(dest_file_name, "w") as dest_file:

                dest_file.write(cpp_header + str(ast))

        except CompileException as e:

            print("Could not compile:")
            print(e)

if __name__ == "__main__":

    main()

