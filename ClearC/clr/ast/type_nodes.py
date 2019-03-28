from collections import namedtuple
from clr.errors import parse_error
from clr.tokens import TokenType
from clr.ast.type_annotations import FunctionTypeAnnotation, SIMPLE_TYPES

SimpleType = namedtuple("SimpleType", ("token", "as_annotation"))


def parse_simple_type(parser):
    err = parse_error("Expected simple type!", parser)
    parser.consume(TokenType.IDENTIFIER, err)
    if parser.get_prev().lexeme not in SIMPLE_TYPES:
        err()
    token = parser.get_prev()
    as_annotation = SIMPLE_TYPES[token.lexeme]
    return SimpleType(token, as_annotation)


FunctionType = namedtuple("FunctionType", ("params", "return_type", "as_annotation"))


def parse_function_type(parser):
    parser.consume(TokenType.FUNC, parse_error("Expected function type!", parser))
    parser.consume(
        TokenType.LEFT_PAREN, parse_error("Expected parameter types!", parser)
    )
    params = []
    while not parser.match(TokenType.RIGHT_PAREN):
        param_type = parse_type(parser)
        params.append(param_type)
        if not parser.check(TokenType.RIGHT_PAREN):
            parser.consume(
                TokenType.COMMA,
                parse_error("Expected comma to delimit parameters!", parser),
            )
    return_type = parse_type(parser)
    as_annotation = FunctionTypeAnnotation(
        return_type=return_type.as_annotation,
        signature=list(map(lambda param: param.as_annotation, params)),
    )
    return FunctionType(params, return_type, as_annotation)


def parse_type(parser):
    if parser.get_current().lexeme in SIMPLE_TYPES:
        return parse_simple_type(parser)
    if parser.get_current().token_type == TokenType.FUNC:
        return parse_function_type(parser)
    parse_error("Expected type!", parser)()
    return None  # unreachable
