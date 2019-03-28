from clr.values import OpCode, DEBUG
from clr.errors import emit_error


class ClrInt:
    def __init__(self, value):
        self.value = int(value)

    def __repr__(self):
        return f"ClrInt({self.value})"

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value) ^ 7

    def __eq__(self, other):
        return isinstance(other, ClrInt) and self.value == other.value


class ClrUint:
    def __init__(self, value):
        if value < 0:
            emit_error(f"Uint created with negative value {value}!")()
        self.value = int(value)

    def __repr__(self):
        return f"ClrUint({self.value})"

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value) ^ 73

    def __eq__(self, other):
        return isinstance(other, ClrUint) and self.value == other.value


class ClrNum:
    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return f"ClrNum({self.value})"

    def __str__(self):
        return str(self.value)

    def __hash__(self):
        return hash(self.value) ^ 43

    def __eq__(self, other):
        return isinstance(other, ClrNum) and self.value == other.value


class ClrStr:
    def __init__(self, value):
        self.value = str(value)

    def __repr__(self):
        return f"ClrStr({self.value})"

    def __str__(self):
        return str(self.value).replace('"', '""')

    def __hash__(self):
        return hash(self.value) ^ 19

    def __eq__(self, other):
        return isinstance(other, ClrStr) and self.value == other.value


class Constants:
    def __init__(self):
        self.values = []
        self.count = 0
        self.code_list = []

    def __iter__(self):
        return iter(self.values)

    def __next__(self):
        return next(self.values)

    def add_all(self, other):
        for item in other:
            self.add(item)

    def add(self, value):
        if value in self.values:
            return self.values.index(value)
        index = self.count
        if DEBUG:
            print(f"Adding constant {index}:{value}")
        self.values.append(value)
        self.count += 1
        return index

    def _store(self, value):
        try:
            op_type = {
                ClrNum: OpCode.NUMBER,
                ClrStr: OpCode.STRING,
                ClrInt: OpCode.INTEGER,
            }[type(value)]
        except KeyError:
            emit_error(f"Unknown constant value type: {type(value)}")()
        self.code_list.append(op_type)
        self.code_list.append(value)

    def flush(self):
        self.code_list.append(ClrUint(len(self.values)))
        for value in self.values:
            self._store(value)
        return self.code_list
