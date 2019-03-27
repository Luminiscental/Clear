from enum import Enum
from collections import namedtuple
from clr.errors import parse_error
from clr.tokens import TokenType
from clr.ast.tree import AstNode
from clr.values import OpCode


class Type(Enum):
    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    FUNCTION = "<function>"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


class Return(Enum):
    NEVER = "<never>"
    SOMETIMES = "<sometimes>"
    ALWAYS = "<always>"

    def __str__(self):
        return self.value


class FuncInfo:
    def __init__(self, return_type, signature):
        self.return_type = return_type
        self.signature = signature

    def __str__(self):
        return (
            "func(" + ", ".join(map(str, self.signature)) + ") " + str(self.return_type)
        )

    def __eq__(self, other):
        return (
            isinstance(other, FuncInfo)
            and self.return_type == other.return_type
            and self.signature == other.signature
        )


class TypeAnnotation:
    def __init__(self, kind=Type.UNRESOLVED, func_info=None):
        self.kind = kind
        self.func_info = func_info

    def __repr__(self):
        if self.kind == Type.FUNCTION:
            return str(self.func_info)
        return str(self.kind)

    def __eq__(self, other):
        if not isinstance(other, TypeAnnotation):
            return False
        if self.kind != other.kind:
            return False
        if self.kind == Type.FUNCTION:
            return self.func_info == other.func_info
        return True


class ReturnAnnotation:
    def __init__(self, kind=Return.NEVER, return_type=None):
        self.kind = kind
        self.return_type = return_type


def parse_type(parser):
    """
    This function parses a type node for the AST from the parser, emitting an error if the tokens
    don't form a valid type.

    Parameters:
        - parser : the Parser instance to read tokens from.

    Returns:
        the type node that was parsed.
    """
    if parser.get_current().lexeme in SIMPLE_TYPES:
        return SimpleType(parser)
    return FunctionType(parser)


class TypeNode(AstNode):
    def __init__(self, parser):
        super().__init__(parser)

    def as_annotation(self):
        return TypeAnnotation()


class SimpleType(TypeNode):
    def __init__(self, parser):
        super().__init__(parser)
        err = parse_error("Expected simple type!", parser)
        parser.consume(TokenType.IDENTIFIER, err)
        if parser.get_prev().lexeme not in SIMPLE_TYPES:
            err()
        self.value = parser.get_prev()

    def as_annotation(self):
        return SIMPLE_TYPES[self.value.lexeme]


class FunctionType(TypeNode):
    def __init__(self, parser):
        super().__init__(parser)
        parser.consume(TokenType.FUNC, parse_error("Expected function type!", parser))
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected parameter types!", parser)
        )
        self.params = []
        while not parser.match(TokenType.RIGHT_PAREN):
            self.params.append(parse_type(parser))
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )
        self.return_type = parse_type(parser)

    def as_annotation(self):
        func_info = FuncInfo(
            return_type=self.return_type.as_annotation(),
            signature=list(map(lambda param: param.as_annotation(), self.params)),
        )
        return TypeAnnotation(kind=Type.FUNCTION, func_info=func_info)


INT_TYPE = TypeAnnotation(kind=Type.INT)
NUM_TYPE = TypeAnnotation(kind=Type.NUM)
STR_TYPE = TypeAnnotation(kind=Type.STR)
BOOL_TYPE = TypeAnnotation(kind=Type.BOOL)

SIMPLE_TYPES = {"int": INT_TYPE, "num": NUM_TYPE, "str": STR_TYPE, "bool": BOOL_TYPE}

Builtin = namedtuple("Builtin", ("signatures", "opcode", "return_type"))

BUILTINS = {
    "clock": Builtin(signatures=[[]], opcode=OpCode.CLOCK, return_type=NUM_TYPE),
    "int": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.INT,
        return_type=INT_TYPE,
    ),
    "num": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.NUM,
        return_type=NUM_TYPE,
    ),
    "str": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [STR_TYPE], [BOOL_TYPE]],
        opcode=OpCode.STR,
        return_type=STR_TYPE,
    ),
    "bool": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.BOOL,
        return_type=BOOL_TYPE,
    ),
}
