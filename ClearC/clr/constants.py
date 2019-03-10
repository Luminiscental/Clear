"""
This module provides classes for creating and indexing constant values for Clear programs.
"""
from clr.values import OpCode, DEBUG
from clr.errors import emit_error


class ClrInt:
    """
    This class wraps an integer value in Clear,
    implementing type-checking comparisons for use in dictionaries.
    """

    def __init__(self, value):
        self.value = int(value)

    def __repr__(self):
        return f"ClrInt({self.value})"

    def __hash__(self):
        return hash(self.value) ^ 7

    def __eq__(self, other):
        return isinstance(other, ClrInt) and self.value == other.value


class ClrUint:
    """
    This class wraps an unsigned integer value in Clear,
    implementing type-checking comparisons for use in dictionaries.
    """

    def __init__(self, value):
        if value < 0:
            emit_error(f"Uint created with negative value {value}!")()
        self.value = int(value)

    def __repr__(self):
        return f"ClrUint({self.value})"

    def __hash__(self):
        return hash(self.value) ^ 73

    def __eq__(self, other):
        return isinstance(other, ClrUint) and self.value == other.value


class ClrNum:
    """
    This class wraps a number value in Clear,
    implementing type-checking comparisons for use in dictionaries.
    """

    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return f"ClrNum({self.value})"

    def __hash__(self):
        return hash(self.value) ^ 43

    def __eq__(self, other):
        return isinstance(other, ClrNum) and self.value == other.value


class ClrStr:
    """
    This class wraps an string value in Clear,
    implementing type-checking comparisons for use in dictionaries.
    """

    def __init__(self, value):
        self.value = str(value)

    def __repr__(self):
        return f"ClrStr({self.value})"

    def __hash__(self):
        return hash(self.value) ^ 19

    def __eq__(self, other):
        return isinstance(other, ClrStr) and self.value == other.value


class Constants:
    """
    This class stores a list of constants to be used in a Clear program
    indexed to emit bytecode storing them for later use.
    """

    def __init__(self):
        self.values = []
        self.count = 0
        self.code_list = []

    def add(self, value):
        """
        This function takes a constant value and returns an index to it within the list;
        adding it if it isn't already present.
        """
        if value in self.values:
            return self.values.index(value)
        index = self.count
        if DEBUG:
            print(f"Adding constant {index}:{value}")
        self.values.append(value)
        self.count += 1
        return index

    def _store(self, value):
        self.code_list.append(OpCode.STORE_CONST)
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
        """
        This function returns a list of bytecode to store all the constant values.
        """
        for value in self.values:
            self._store(value)
        return self.code_list
