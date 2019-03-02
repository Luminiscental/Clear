
from clr.values import OpCode, debug
from clr.errors import emit_error

class Index:

    def __init__(self, index):
        self.value = index

class ClrInt:

    def __init__(self, value):
        self.value = int(value)

    def __repr__(self):
        return f'ClrInt({self.value})'

    def __hash__(self):
        return hash(self.value) ^ 7

    def __eq__(self, other):
        return isinstance(other, ClrInt) and self.value == other.value

class ClrNum:

    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return f'ClrNum({self.value})'

    def __hash__(self):
        return hash(self.value) ^ 43

    def __eq__(self, other):
        return isinstance(other, ClrNum) and self.value == other.value

class ClrStr:

    def __init__(self, value):
        self.value = str(value)

    def __repr__(self):
        return f'ClrStr({self.value})'

    def __hash__(self):
        return hash(self.value) ^ 19

    def __eq__(self, other):
        return isinstance(other, ClrStr) and self.value == other.value

class Constants:

    def __init__(self):
        self.values = []
        self.count = 0
        self.code_list = []

    def add(self, value):
        if value in self.values:
            return Index(self.values.index(value))
        else:
            if debug:
                if isinstance(value, ClrStr):
                    print(f'Adding constant {self.count}:"{value}"')
                else:
                    print(f'Adding constant {self.count}:{value}')
            self.values.append(value)
            self.count += 1
            return Index(self.count - 1)

    def store(self, value):
        self.code_list.append(OpCode.STORE_CONST)
        op_type = {
            ClrNum: lambda: OpCode.NUMBER,
            ClrStr: lambda: OpCode.STRING,
            ClrInt: lambda: OpCode.INTEGER
        }.get(type(value), emit_error(
            f'Unknown constant value type: {type(value)}'
        ))()
        self.code_list.append(op_type)
        self.code_list.append(value)

    def flush(self):
        for value in self.values:
            self.store(value)
        return self.code_list

