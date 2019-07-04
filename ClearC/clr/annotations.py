"""
Contains definitions for annotations of the ast.
"""

import enum
import dataclasses as dc

# Return annotations


@enum.unique
class ReturnAnnot(enum.Enum):
    """
    Enumerates the different kinds of control flow for parts of code, either they always return,
    sometimes return, or never return.
    """

    NEVER = enum.auto()
    SOMETIMES = enum.auto()
    ALWAYS = enum.auto()

    def __str__(self) -> str:
        return self.name


# Index annotations


@enum.unique
class IndexAnnotType(enum.Enum):
    """
    Enumerates the possible types of index.
    """

    GLOBAL = enum.auto()
    LOCAL = enum.auto()
    UPVALUE = enum.auto()
    PARAM = enum.auto()
    UNRESOLVED = enum.auto()

    def __str__(self) -> str:
        return self.name


@dc.dataclass
class IndexAnnot:
    """
    Annotation for the index and type of a value reference.
    """

    value: int
    kind: IndexAnnotType

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IndexAnnot):
            return self.kind == other.kind and self.value == other.value
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def __str__(self) -> str:
        return f"{self.kind}:{self.value}"
