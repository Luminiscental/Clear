"""
Module containing definitions for a Clear ast and a base class for ast visitors.
"""

from typing import Union, List, Optional, Tuple, Dict

import clr.errors as er
import clr.lexer as lx

TypeAnnot = Union["BuiltinTypeAnnot", "FuncTypeAnnot", "OptionalTypeAnnot", None]

Comparison = Union[bool, "NotImplemented"]


class BuiltinTypeAnnot:
    """
    Type annotation for a built in type.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return self.name == other.name
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        if other is None:
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class FuncTypeAnnot:
    """
    Type annotation for a function type.
    """

    def __init__(self, params: List[TypeAnnot], return_type: TypeAnnot) -> None:
        self.params = params
        self.return_type = return_type

    def __str__(self) -> str:
        param_str = ", ".join(str(param) for param in self.params)
        return f"func({param_str}) {self.return_type}"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return self.params == other.params and self.return_type == other.return_type
        if isinstance(other, OptionalTypeAnnot):
            return False
        if other is None:
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class OptionalTypeAnnot:
    """
    Type annotation for an optional type.
    """

    def __init__(self, target: TypeAnnot) -> None:
        self.target = target

    def __str__(self) -> str:
        return f"({self.target})?"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return self.target == other.target
        if other is None:
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class AstVisitor:
    """
    Base class for an ast visitor.
    """

    def value_decl(self, node: "AstValueDecl") -> None:
        """
        Visit a value declaration node.
        """

    def func_decl(self, node: "AstFuncDecl") -> None:
        """
        Visit a function declaration node.
        """

    def param(self, node: "AstParam") -> None:
        """
        Visit a parameter declaration node.
        """

    def print_stmt(self, node: "AstPrintStmt") -> None:
        """
        Visit a print statement node.
        """

    def block_stmt(self, node: "AstBlockStmt") -> None:
        """
        Visit a block statement node.
        """

    def if_stmt(self, node: "AstIfStmt") -> None:
        """
        Visit an if statement node.
        """

    def while_stmt(self, node: "AstWhileStmt") -> None:
        """
        Visit a while statement node.
        """

    def return_stmt(self, node: "AstReturnStmt") -> None:
        """
        Visit a return statement node.
        """

    def expr_stmt(self, node: "AstExprStmt") -> None:
        """
        Visit an expression statement.
        """

    def unary_expr(self, node: "AstUnaryExpr") -> None:
        """
        Visit a unary expression node.
        """

    def binary_expr(self, node: "AstBinaryExpr") -> None:
        """
        Visit a binary expression node.
        """

    def int_expr(self, node: "AstIntExpr") -> None:
        """
        Visit an int literal.
        """

    def num_expr(self, node: "AstNumExpr") -> None:
        """
        Visit a num literal.
        """

    def str_expr(self, node: "AstStrExpr") -> None:
        """
        Visit a str literal.
        """

    def ident_expr(self, node: "AstIdentExpr") -> None:
        """
        Visit an identifier expression.
        """

    def bool_expr(self, node: "AstBoolExpr") -> None:
        """
        Visit a boolean expression.
        """

    def call_expr(self, node: "AstCallExpr") -> None:
        """
        Visit a function call expression node.
        """

    def atom_type(self, node: "AstAtomType") -> None:
        """
        Visit an atomic type node.
        """

    def func_type(self, node: "AstFuncType") -> None:
        """
        Visit a function type node.
        """

    def optional_type(self, node: "AstOptionalType") -> None:
        """
        Visit an optional type node.
        """


class DeepVisitor(AstVisitor):
    """
    Ast visitor that propogates to all nodes for a convenient base class.
    """

    def value_decl(self, node: "AstValueDecl") -> None:
        node.val_init.accept(self)
        if node.val_type:
            node.val_type.accept(self)

    def func_decl(self, node: "AstFuncDecl") -> None:
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)
        node.block.accept(self)

    def param(self, node: "AstParam") -> None:
        node.param_type.accept(self)

    def print_stmt(self, node: "AstPrintStmt") -> None:
        if node.expr:
            node.expr.accept(self)

    def block_stmt(self, node: "AstBlockStmt") -> None:
        for decl in node.decls:
            decl.accept(self)

    def if_stmt(self, node: "AstIfStmt") -> None:
        node.if_part[0].accept(self)
        node.if_part[1].accept(self)
        for cond, block in node.elif_parts:
            cond.accept(self)
            block.accept(self)
        if node.else_part:
            node.else_part.accept(self)

    def while_stmt(self, node: "AstWhileStmt") -> None:
        if node.cond:
            node.cond.accept(self)
        node.block.accept(self)

    def return_stmt(self, node: "AstReturnStmt") -> None:
        if node.expr:
            node.expr.accept(self)

    def expr_stmt(self, node: "AstExprStmt") -> None:
        node.expr.accept(self)

    def unary_expr(self, node: "AstUnaryExpr") -> None:
        node.target.accept(self)

    def binary_expr(self, node: "AstBinaryExpr") -> None:
        node.left.accept(self)
        node.right.accept(self)

    def call_expr(self, node: "AstCallExpr") -> None:
        node.function.accept(self)
        for arg in node.args:
            arg.accept(self)

    def func_type(self, node: "AstFuncType") -> None:
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)

    def optional_type(self, node: "AstOptionalType") -> None:
        node.target.accept(self)


class AstNode:
    """
    Base class for an ast node that can accept a visitor.
    """

    def __init__(self) -> None:
        self.type_annot: TypeAnnot = None

    def accept(self, visitor: AstVisitor) -> None:
        """
        Accept a visitor to this node, calling the relevant method of the visitor.
        """
        raise NotImplementedError()


AstType = Union["AstAtomType", "AstFuncType", "AstOptionalType"]
AstAtomExpr = Union[
    "AstIntExpr", "AstNumExpr", "AstStrExpr", "AstIdentExpr", "AstBoolExpr"
]
AstExpr = Union["AstUnaryExpr", "AstBinaryExpr", "AstAtomExpr", "AstCallExpr"]
AstStmt = Union[
    "AstPrintStmt",
    "AstBlockStmt",
    "AstIfStmt",
    "AstWhileStmt",
    "AstReturnStmt",
    "AstExprStmt",
]
AstDecl = Union["AstValueDecl", "AstFuncDecl", AstStmt]


class AstError(Exception, AstNode):
    """
    Ast node to represent an error creating the tree.
    """

    def __init__(self) -> None:
        super().__init__("incomplete parse")

    def accept(self, visitor: AstVisitor) -> None:
        # TODO: Do something more reasonable here, maybe visitor.error(self)
        raise self


class Ast(AstNode):
    """
    The root ast node.
    """

    def __init__(self, decls: List[AstDecl]) -> None:
        super().__init__()
        self.decls = decls
        # Annotations:
        self.names: Dict[str, Union[AstFuncDecl, AstValueDecl, AstParam]] = {}

    def accept(self, visitor: AstVisitor) -> None:
        for decl in self.decls:
            decl.accept(visitor)

    @staticmethod
    def make(decls: List[Union[AstDecl, AstError]]) -> Union["Ast", AstError]:
        """
        Makes the node or returns an error given a list of declarations that may include errors.
        """
        pure = []
        for decl in decls:
            if isinstance(decl, AstError):
                return decl
            pure.append(decl)
        return Ast(pure)


class AstValueDecl(AstNode):
    """
    Ast node for a value declaration.
    """

    def __init__(
        self,
        ident: str,
        val_type: Optional[AstType],
        val_init: AstExpr,
        region: er.SourceView,
    ):
        super().__init__()
        self.ident = ident
        self.val_type = val_type
        self.val_init = val_init
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.value_decl(self)

    @staticmethod
    def make(
        ident: Union[lx.Token, AstError],
        val_type: Optional[Union[AstType, AstError]],
        val_init: Union[AstExpr, AstError],
        region: er.SourceView,
    ) -> Union["AstValueDecl", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(ident, AstError):
            return ident
        pure_type = None
        if val_type:
            if isinstance(val_type, AstError):
                return val_type
            pure_type = val_type
        if isinstance(val_init, AstError):
            return val_init
        pure_init = val_init
        return AstValueDecl(str(ident), pure_type, pure_init, region)


class AstParam(AstNode):
    """
    Ast node for a parameter declaration.
    """

    def __init__(self, param_type: AstType, param_name: lx.Token) -> None:
        super().__init__()
        self.param_type = param_type
        self.param_name = str(param_name)
        self.region = er.SourceView.range(param_type.region, param_name.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.param(self)

    @staticmethod
    def make(
        param_type: Union[AstType, AstError], param_name: Union[lx.Token, AstError]
    ) -> Union["AstParam", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(param_type, AstError):
            return param_type
        if isinstance(param_name, AstError):
            return param_name
        return AstParam(param_type, param_name)


class AstFuncDecl(AstNode):
    """
    Ast node for a function declaration.
    """

    def __init__(
        self,
        ident: str,
        params: List[AstParam],
        return_type: AstType,
        block: "AstBlockStmt",
        region: er.SourceView,
    ) -> None:
        super().__init__()
        self.ident = ident
        self.params = params
        self.return_type = return_type
        self.block = block
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.func_decl(self)

    @staticmethod
    def make(
        ident: Union[lx.Token, AstError],
        params: List[Tuple[Union[AstType, AstError], Union[lx.Token, AstError]]],
        return_type: Union[AstType, AstError],
        block: Union["AstBlockStmt", AstError],
        region: er.SourceView,
    ) -> Union["AstFuncDecl", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(ident, AstError):
            return ident
        pure_params = []
        for param_type, param_ident in params:
            param = AstParam.make(param_type, param_ident)
            if isinstance(param, AstError):
                return param
            pure_params.append(param)
        if isinstance(return_type, AstError):
            return return_type
        if isinstance(block, AstError):
            return block
        return AstFuncDecl(str(ident), pure_params, return_type, block, region)


class AstPrintStmt(AstNode):
    """
    Ast node for a print statement.
    """

    def __init__(self, expr: Optional[AstExpr]) -> None:
        super().__init__()
        self.expr = expr

    def accept(self, visitor: AstVisitor) -> None:
        visitor.print_stmt(self)

    @staticmethod
    def make(
        expr: Optional[Union[AstExpr, AstError]]
    ) -> Union["AstPrintStmt", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if expr:
            if isinstance(expr, AstError):
                return expr
            return AstPrintStmt(expr)
        return AstPrintStmt(None)


class AstBlockStmt(AstNode):
    """
    Ast node for a block statement.
    """

    def __init__(self, decls: List[AstDecl]) -> None:
        super().__init__()
        self.decls = decls
        # Annotations:
        self.names: Dict[str, Union[AstFuncDecl, AstValueDecl, AstParam]] = {}

    def accept(self, visitor: AstVisitor) -> None:
        visitor.block_stmt(self)

    @staticmethod
    def make(decls: List[Union[AstDecl, AstError]]) -> Union["AstBlockStmt", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        pure_decls = []
        for decl in decls:
            if isinstance(decl, AstError):
                return decl
            pure_decls.append(decl)
        return AstBlockStmt(pure_decls)


class AstIfStmt(AstNode):
    """
    Ast node for an if statement.
    """

    def __init__(
        self,
        if_part: Tuple[AstExpr, AstBlockStmt],
        elif_parts: List[Tuple[AstExpr, AstBlockStmt]],
        else_part: Optional[AstBlockStmt],
    ) -> None:
        super().__init__()
        self.if_part = if_part
        self.elif_parts = elif_parts
        self.else_part = else_part

    def accept(self, visitor: AstVisitor) -> None:
        visitor.if_stmt(self)

    @staticmethod
    def make(
        if_part: Tuple[Union[AstExpr, AstError], Union[AstBlockStmt, AstError]],
        elif_parts: List[
            Tuple[Union[AstExpr, AstError], Union[AstBlockStmt, AstError]]
        ],
        else_part: Optional[Union[AstBlockStmt, AstError]],
    ) -> Union["AstIfStmt", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if_cond, if_block = if_part
        if isinstance(if_cond, AstError):
            return if_cond
        if isinstance(if_block, AstError):
            return if_block
        pure_elifs = []
        for elif_cond, elif_block in elif_parts:
            if isinstance(elif_cond, AstError):
                return elif_cond
            if isinstance(elif_block, AstError):
                return elif_block
            pure_elifs.append((elif_cond, elif_block))
        if else_part:
            if isinstance(else_part, AstError):
                return else_part
            pure_else: Optional[AstBlockStmt] = else_part
        else:
            pure_else = None
        return AstIfStmt((if_cond, if_block), pure_elifs, pure_else)


class AstWhileStmt(AstNode):
    """
    Ast node for a while statement.
    """

    def __init__(self, cond: Optional[AstExpr], block: AstBlockStmt) -> None:
        super().__init__()
        self.cond = cond
        self.block = block

    def accept(self, visitor: AstVisitor) -> None:
        visitor.while_stmt(self)

    @staticmethod
    def make(
        cond: Optional[Union[AstExpr, AstError]], block: Union[AstBlockStmt, AstError]
    ) -> Union["AstWhileStmt", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(block, AstError):
            return block
        if cond:
            if isinstance(cond, AstError):
                return cond
            return AstWhileStmt(cond, block)
        return AstWhileStmt(None, block)


class AstReturnStmt(AstNode):
    """
    Ast node for a return statement.
    """

    def __init__(self, expr: Optional[AstExpr], region: er.SourceView) -> None:
        super().__init__()
        self.expr = expr
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.return_stmt(self)

    @staticmethod
    def make(
        expr: Optional[Union[AstExpr, AstError]], region: er.SourceView
    ) -> Union["AstReturnStmt", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if expr:
            if isinstance(expr, AstError):
                return expr
            return AstReturnStmt(expr, region)
        return AstReturnStmt(None, region)


class AstExprStmt(AstNode):
    """
    Ast node for an expression statement.
    """

    def __init__(self, expr: AstExpr) -> None:
        super().__init__()
        self.expr = expr

    def accept(self, visitor: AstVisitor) -> None:
        visitor.expr_stmt(self)

    @staticmethod
    def make(expr: Union[AstExpr, AstError]) -> Union["AstExprStmt", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(expr, AstError):
            return expr
        return AstExprStmt(expr)


class AstUnaryExpr(AstNode):
    """
    Ast node for a unary expression.
    """

    def __init__(
        self, operator: lx.Token, target: AstExpr, region: er.SourceView
    ) -> None:
        super().__init__()
        self.operator = operator
        self.target = target
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.unary_expr(self)

    @staticmethod
    def make(
        operator: lx.Token, target: Union[AstExpr, AstError], region: er.SourceView
    ) -> Union["AstUnaryExpr", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(target, AstError):
            return target
        return AstUnaryExpr(operator, target, region)


class AstBinaryExpr(AstNode):
    """
    Ast node for a binary expression.
    """

    def __init__(
        self, operator: lx.Token, left: AstExpr, right: AstExpr, region: er.SourceView
    ) -> None:
        super().__init__()
        self.operator = operator
        self.left = left
        self.right = right
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.binary_expr(self)

    @staticmethod
    def make(
        operator: lx.Token,
        left: Union[AstExpr, AstError],
        right: Union[AstExpr, AstError],
        region: er.SourceView,
    ) -> Union["AstBinaryExpr", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(left, AstError):
            return left
        if isinstance(right, AstError):
            return right
        return AstBinaryExpr(operator, left, right, region)


class AstIntExpr(AstNode):
    """
    Ast node for an int literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__()
        self.literal = str(literal)
        self.region = literal.lexeme

    def accept(self, visitor: AstVisitor) -> None:
        visitor.int_expr(self)


class AstNumExpr(AstNode):
    """
    Ast node for a num literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__()
        self.literal = str(literal)
        self.region = literal.lexeme

    def accept(self, visitor: AstVisitor) -> None:
        visitor.num_expr(self)


class AstStrExpr(AstNode):
    """
    Ast node for a str literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__()
        self.literal = str(literal)
        self.region = literal.lexeme

    def accept(self, visitor: AstVisitor) -> None:
        visitor.str_expr(self)


AstIdentRef = Union[AstFuncDecl, AstValueDecl, AstParam]


class AstIdentExpr(AstNode):
    """
    Ast node for an identifier expression.
    """

    def __init__(self, token: lx.Token) -> None:
        super().__init__()
        self.region = token.lexeme
        self.name = str(token)
        # Annotations:
        self.ref: Optional[AstIdentRef] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.ident_expr(self)


class AstBoolExpr(AstNode):
    """
    Ast node for a boolean expression.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__()
        self.value = str(literal) == "true"
        self.region = literal.lexeme

    def accept(self, visitor: AstVisitor) -> None:
        visitor.bool_expr(self)


class AstCallExpr(AstNode):
    """
    Ast node for a function call expression.
    """

    def __init__(
        self, function: AstExpr, args: List[AstExpr], region: er.SourceView
    ) -> None:
        super().__init__()
        self.function = function
        self.args = args
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.call_expr(self)

    @staticmethod
    def make(
        function: Union[AstExpr, AstError],
        args: List[Union[AstExpr, AstError]],
        region: er.SourceView,
    ) -> Union["AstCallExpr", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(function, AstError):
            return function
        pure_args = []
        for arg in args:
            if isinstance(arg, AstError):
                return arg
            pure_args.append(arg)
        return AstCallExpr(function, pure_args, region)


class AstAtomType(AstNode):
    """
    Ast node for an atomic type.
    """

    def __init__(self, token: lx.Token) -> None:
        super().__init__()
        self.region = token.lexeme
        self.name = str(token)
        # Annotations:
        self.ref: Optional[Union[AstFuncDecl, AstValueDecl, AstParam]] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.atom_type(self)

    @staticmethod
    def make(token: Union[lx.Token, AstError]) -> Union["AstAtomType", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(token, AstError):
            return token
        return AstAtomType(token)


class AstFuncType(AstNode):
    """
    Ast node for a function type.
    """

    def __init__(
        self, params: List[AstType], return_type: AstType, region: er.SourceView
    ) -> None:
        super().__init__()
        self.params = params
        self.return_type = return_type
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.func_type(self)

    @staticmethod
    def make(
        params: List[Union[AstType, AstError]],
        return_type: Union[AstType, AstError],
        region: er.SourceView,
    ) -> Union["AstFuncType", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        pure_params = []
        for param in params:
            if isinstance(param, AstError):
                return param
            pure_params.append(param)
        if isinstance(return_type, AstError):
            return return_type
        return AstFuncType(pure_params, return_type, region)


class AstOptionalType(AstNode):
    """
    Ast node for an optional type.
    """

    def __init__(self, target: AstType, region: er.SourceView) -> None:
        super().__init__()
        self.target = target
        self.region = region

    def accept(self, visitor: AstVisitor) -> None:
        visitor.optional_type(self)

    @staticmethod
    def make(
        target: Union[AstType, AstError], region: er.SourceView
    ) -> Union["AstOptionalType", AstError]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if isinstance(target, AstError):
            return target
        return AstOptionalType(target, region)
