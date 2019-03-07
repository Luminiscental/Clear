from clr.tokens import token_info, tokenize
from clr.errors import emit_error
from clr.assemble import assemble, assembled_size
from clr.constants import Constants, ClrNum, ClrInt, ClrUint, ClrStr
from clr.values import OpCode, DEBUG


class LocalVariables:
    def __init__(self):
        self.scopes = []
        self.level = -1
        self.index = 0

    def scoped(self):
        return self.level > -1

    def _current_scope(self):
        if not self.scoped():
            emit_error("Global scope is not local!")()
        return self.scopes[self.level]

    def _get_scope(self, lookback):
        if not self.scoped():
            emit_error("Global scope is not local!")()
        return self.scopes[self.level - lookback]

    def push_scope(self):
        self.scopes.append({})
        self.level += 1
        if DEBUG:
            print(f"Pushed scope, level is now {self.level}")

    def pop_scope(self):
        if not self.scoped():
            emit_error("Cannot pop scope at global scope!")()
        popped_scope = self._current_scope()
        if popped_scope:
            self.index = min(popped_scope.values())
        del self.scopes[self.level]
        self.level -= 1
        if DEBUG:
            print(f"Popped scope, level is now {self.level}, index is now {self.index}")

    def get_name(self, name):
        result = None
        if not self.scoped():
            return result
        lookback = 0
        while result is None:
            try:
                result = self._get_scope(lookback).get(name, None)
                lookback += 1
            except IndexError:
                break
        return result

    def add_name(self, name):
        if not self.scoped():
            emit_error("Cannot define local variable in global scope!")()
        index = self.get_name(name)
        if index is not None:
            return index
        new_index = self.index
        self.index += 1
        self._current_scope()[name] = new_index
        if DEBUG:
            print(
                f"Defined local name {name} at level {self.level}, index is now {self.index}"
            )
        return new_index


class GlobalVariables:
    def __init__(self):
        self.indices = {}
        self.index = 0

    def get_name(self, name):
        return self.indices.get(name, None)

    def add_name(self, name):
        index = self.get_name(name)
        if index is not None:
            return index
        new_index = self.index
        self.index += 1
        self.indices[name] = new_index
        if DEBUG:
            print(f"Defined global name {name}, index is now {self.index}")
        return new_index


class Program:
    def __init__(self):
        self.code_list = []
        self.global_variables = GlobalVariables()
        self.local_variables = LocalVariables()

    def load_constant(self, constant):
        self.code_list.append(OpCode.LOAD_CONST)
        self.code_list.append(constant)

    def simple_op(self, opcode):
        self.code_list.append(opcode)

    def push_scope(self):
        self.local_variables.push_scope()
        self.simple_op(OpCode.PUSH_SCOPE)

    def pop_scope(self):
        self.local_variables.pop_scope()
        self.simple_op(OpCode.POP_SCOPE)

    def define_name(self, name):
        if self.local_variables.scoped():
            index = self.local_variables.add_name(name)
            self.code_list.append(OpCode.DEFINE_LOCAL)
        else:
            index = self.global_variables.add_name(name)
            self.code_list.append(OpCode.DEFINE_GLOBAL)
        self.code_list.append(index)

    def load_name(self, name, err):
        opcode = OpCode.LOAD_LOCAL
        index = self.local_variables.get_name(name)
        if index is None:
            opcode = OpCode.LOAD_GLOBAL
            index = self.global_variables.get_name(name)
            if index is None:
                err()
        self.code_list.append(opcode)
        self.code_list.append(index)

    def begin_jump(self, conditional=False, leave_value=False):
        self.code_list.append(OpCode.JUMP_IF_NOT if conditional else OpCode.JUMP)
        index = len(self.code_list)
        if DEBUG:
            print(f"Defining a jump from {index}")
        temp_offset = ClrUint(0)
        self.code_list.append(temp_offset)
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)
        return index, conditional

    def end_jump(self, jump_ref, leave_value=False):
        index, conditional = jump_ref
        contained = self.code_list[index + 1 :]
        offset = assembled_size(contained)
        if DEBUG:
            print(f"Jump from index set with offset {offset}")
        self.code_list[index] = ClrUint(offset)
        if conditional and not leave_value:
            self.code_list.append(OpCode.POP)

    def flush(self):
        return self.code_list


class Parser:
    def __init__(self, tokens):
        self.index = 0
        self.tokens = tokens
        self.constants = Constants()
        self.program = Program()

    def get_current(self):
        return self.tokens[self.index]

    def get_prev(self):
        return self.tokens[self.index - 1]

    def current_info(self):
        return token_info(self.get_current())

    def prev_info(self):
        return token_info(self.get_prev())

    def advance(self):
        self.index += 1

    def check(self, token_type):
        return self.get_current().token_type == token_type

    def match(self, expected_type):
        if not self.check(expected_type):
            return False
        self.advance()
        return True

    def consume(self, expected_type, err):
        if not self.match(expected_type):
            err()

    def consume_one(self, possibilities, err):
        if not possibilities:
            err()
        elif not self.match(possibilities[0]):
            self.consume_one(possibilities[1:], err)

    def flush(self):
        return self.constants.flush() + self.program.flush()


def parse_source(source):

    tokens = tokenize(source)
    if DEBUG:
        print("Tokens:")
        print(" ".join([token.lexeme for token in tokens]))
    return Parser(tokens)
