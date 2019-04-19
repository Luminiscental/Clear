from enum import Enum


class IndexAnnotationType(Enum):
    UNRESOLVED = "<unresolved>"
    PARAM = "<param>"
    LOCAL = "<local>"
    GLOBAL = "<global>"
    UPVALUE = "<upvalue>"
    PROPERTY = "<property>"

    def __str__(self):
        return self.value


class IndexAnnotation:
    def __init__(self, kind=IndexAnnotationType.UNRESOLVED, value=-1):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return f"IndexAnnotation(kind={self.kind}, value={self.value})"


# Index within the constructor function of the produced instance,
# used for indexing the `this` upvalue of methods
INDEX_OF_THIS = IndexAnnotation(kind=IndexAnnotationType.LOCAL, value=0)
