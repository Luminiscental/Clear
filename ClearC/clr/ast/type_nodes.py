from clr.errors import parse_error
from clr.tokens import TokenType
from clr.ast.type_annotations import FunctionTypeAnnotation, SIMPLE_TYPES


class SimpleType:
    def __init__(self, parser):
        err = parse_error("Expected simple type!", parser)
        parser.consume(TokenType.IDENTIFIER, err)
        if parser.get_prev().lexeme not in SIMPLE_TYPES:
            err()
        self.token = parser.get_prev()
        self.as_annotation = SIMPLE_TYPES[self.token.lexeme]


class FunctionType:
    def __init__(self, parser):
        parser.consume(TokenType.FUNC, parse_error("Expected function type!", parser))
        parser.consume(
            TokenType.LEFT_PAREN, parse_error("Expected parameter types!", parser)
        )
        self.params = []
        while not parser.match(TokenType.RIGHT_PAREN):
            param_type = parse_type(parser)
            self.params.append(param_type)
            if not parser.check(TokenType.RIGHT_PAREN):
                parser.consume(
                    TokenType.COMMA,
                    parse_error("Expected comma to delimit parameters!", parser),
                )
        self.return_type = parse_type(parser)
        self.as_annotation = FunctionTypeAnnotation(
            return_type=self.return_type.as_annotation,
            signature=list(map(lambda param: param.as_annotation, self.params)),
        )


def parse_type(parser):
    if parser.get_current().lexeme in SIMPLE_TYPES:
        return SimpleType(parser)
    if parser.get_current().token_type == TokenType.FUNC:
        return FunctionType(parser)
    parse_error("Expected type!", parser)()
