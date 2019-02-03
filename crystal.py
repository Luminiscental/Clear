
from enum import Enum
import re
import sys

name_re = "[a-zA-Z][a-zA-Z0-9]*"

# 0: val/var, 1: name, 2: type or None, 3: value or None
variable_re_capturing = "(private\s+|public\s+)?(val|var)\s+(" + name_re + ")\s*(?::\s*(" + name_re + "))?(?:(?:\s*=\s*)(.*))?"
variable_re = "(?:private\s+|public\s+)?(?:val|var)\s+(?:" + name_re + ")\s*(?::\s*(?:" + name_re + "))?(?:(?:\s*=\s*)(?:.*))?"

# 0: condition
if_re_capturing = "if\s*\((.*)\)"

# 0: condition
else_if_re_capturing = "else\s+if\s*\((.*)\)"

else_re = "else"

# 0: init, 1: condition, 2: increment
for_re_capturing = "for\s*\((.*)\s*;\s*(.*)\s*;\s*(.*)\)"

# 0: name, 1: params, 2: return type or None
func_re_capturing = "func\s+(" + name_re + ")\s*\(((?:(?:" + variable_re + ")(?:\s*,\s*" + variable_re + ")*)?)\)\s*(?::\s*(" + name_re + "))?"

# 0: name, 1: base class or None
class_re_capturing = "class\s+(" + name_re + ")\s*(?::\s*(" + name_re + "))?"

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

# TODO: __str__

class CrystalReturn:

    # TODO

    def __init__(self, body_node):

        pass

class CrystalParams:

    # TODO

    def __init__(self, param_node):

        pass

class CrystalFunction:

    def __init__(self, name, params, ret, body):

        self.name = name
        self.params = CrystalParams(params)

        if ret:

            ret_match = re.search("\s*:\s*(" + name_re + ")", ret)

            if not ret_match:

                raise CompileException("Invalid return expression for function")

            self.ret = ret_match.groups()[0]

        else:

            self.ret = None

        self.body = CrystalReturn(body)

def parse_block(header, others):

    if isinstance(header, CrystalNode):

        return None, 0

    func_match = re.search("func\s+" + name_re, header)

    if func_match:

        name = func_match.groups()[0]
        params = others[0]

        if not params or not isinstance(params, CrystalNode) or params.type != "(":

            raise CompileException("Function declaration without param block")

        if not others[1]:

            raise CompileException("Function declaration requires body")

        ret = None
        body_index = 1

        if not isinstance(others[1], CrystalNode):

            ret = others[1]
            body_index = 2

        body = others[body_index]

        if not isinstance(body, CrystalNode) or body.type != "{":

            raise CompileException("Function declaration requires a body")

        return CrystalFunction(name, params, ret, body), body_index + 1

    return None

'''
self.type : either "{", "(", or "[" - the type of block this is
self.children : a list of strings and nodes that are contained in this block
self.parent : the block this is a part of, for the root block parent is None
'''

class CrystalNode:

    def __init__(self, opener):

        self.type = opener
        self.children = []
        self.parent = None

    def add_line(self, line):

        self.children.append(line)

    def add_child(self, opener):

        node = CrystalNode(opener)
        node.parent = self
        self.children.append(node)

    def collapse(self):

        new_children = []
        num_children = len(self.children)

        skip_indices = []

        for i in range(0, num_children):

            if i in skip_indices:

                continue

            child = self.children[i]
            after_child = self.children[i + 1:]

            as_block, consumed = parse_block(child, after_child)

            if as_block:

                skip_indices.extend(consumed)
                new_children.append(as_block)

            else:

                new_children.append(child)

        self.children = new_children

'''
self.root : the root block
self.current : the block currently being parsed into
'''

class CrystalAst:

    def __init__(self):

        self.root = CrystalNode()
        self.current = self.root

    def add_line(self, line):

        self.current.add_line(line)

    def push_block(self, opener):

        self.current.add_child(opener)
        self.current = self.current.last_child

    def pop_block(self):

        self.current = self.current.parent

    def parse_line(self, line):

        acc = ""

        for c in line:

            if c == "(" or c == "{" or c == "[":

                add_line(acc)
                acc = ""
                push_block(c)

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

