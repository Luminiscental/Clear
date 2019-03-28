from enum import Enum


class ReturnAnnotationType(Enum):
    NEVER = "<never>"
    SOMETIMES = "<sometimes>"
    ALWAYS = "<always>"

    def __str__(self):
        return self.value


class ReturnAnnotation:
    def __init__(self, kind=ReturnAnnotationType.NEVER, return_type=None):
        self.kind = kind
        self.return_type = return_type
