from enum import Enum
from collections import namedtuple


class ReturnAnnotationType(Enum):
    NEVER = "<never>"
    SOMETIMES = "<sometimes>"
    ALWAYS = "<always>"

    def __str__(self):
        return self.value


ReturnAnnotation = namedtuple(
    "ReturnAnnotation",
    ("kind", "return_type"),
    defaults=(ReturnAnnotationType.NEVER, None),
)
