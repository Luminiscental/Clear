"""
Module containing definitions for a Clear ast and a base class for ast visitors.
"""

from typing import Union, List, Optional, Tuple, Dict

import clr.errors as er
import clr.lexer as lx

TypeAnnot = Union[
    "BuiltinTypeAnnot", "FuncTypeAnnot", "OptionalTypeAnnot", "UnresolvedTypeAnnot"
]

Comparison = Union[bool, "NotImplemented"]


# TODO: Annotation types should probably be with the visitor that uses them but I'm not sure how
class UnresolvedTypeAnnot:
    """
    Type annotation for an unresolved node.
    """

    def __init__(self) -> None:
        self.unresolved = True

    def __str__(self) -> str:
        return "<unresolved>"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        if isinstance(other, UnresolvedTypeAnnot):  # maybe return True here?
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class BuiltinTypeAnnot:
    """
    Type annotation for a built in type.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.unresolved = False

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return self.name == other.name
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        if isinstance(other, UnresolvedTypeAnnot):
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
        self.unresolved = False

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
        if isinstance(other, UnresolvedTypeAnnot):
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
        self.unresolved = False

    def __str__(self) -> str:
        return f"({self.target})?"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return self.target == other.target
        if isinstance(other, UnresolvedTypeAnnot):
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
        self.type_annot: TypeAnnot = UnresolvedTypeAnnot()

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
    def make(decls: List[Optional[AstDecl]]) -> Optional["Ast"]:
        """
        Makes the node or returns an error given a list of declarations that may include errors.
        """
        pure = []
        for decl in decls:
            if decl is None:
                return None
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
        ident: Optional[lx.Token],
        val_type: Optional[Optional[AstType]],
        val_init: Optional[AstExpr],
        region: er.SourceView,
    ) -> Optional["AstValueDecl"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if ident is None:
            return None
        pure_type = None
        if val_type:
            if val_type is None:
                return None
            pure_type = val_type
        if val_init is None:
            return None
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
        param_type: Optional[AstType], param_name: Optional[lx.Token]
    ) -> Optional["AstParam"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if param_type is None:
            return None
        if param_name is None:
            return None
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
        ident: Optional[lx.Token],
        params: List[Tuple[Optional[AstType], Optional[lx.Token]]],
        return_type: Optional[AstType],
        block: Optional["AstBlockStmt"],
        region: er.SourceView,
    ) -> Optional["AstFuncDecl"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if ident is None:
            return None
        pure_params = []
        for param_type, param_ident in params:
            param = AstParam.make(param_type, param_ident)
            if param is None:
                return None
            pure_params.append(param)
        if return_type is None:
            return None
        if block is None:
            return None
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
    def make(expr: Optional[Optional[AstExpr]]) -> Optional["AstPrintStmt"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if expr:
            if expr is None:
                return None
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
    def make(decls: List[Optional[AstDecl]]) -> Optional["AstBlockStmt"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        pure_decls = []
        for decl in decls:
            if decl is None:
                return None
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
        if_part: Tuple[Optional[AstExpr], Optional[AstBlockStmt]],
        elif_parts: List[Tuple[Optional[AstExpr], Optional[AstBlockStmt]]],
        else_part: Optional[Optional[AstBlockStmt]],
    ) -> Optional["AstIfStmt"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if_cond, if_block = if_part
        if if_cond is None:
            return None
        if if_block is None:
            return None
        pure_elifs = []
        for elif_cond, elif_block in elif_parts:
            if elif_cond is None:
                return None
            if elif_block is None:
                return None
            pure_elifs.append((elif_cond, elif_block))
        if else_part:
            if else_part is None:
                return None
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
        cond: Optional[Optional[AstExpr]], block: Optional[AstBlockStmt]
    ) -> Optional["AstWhileStmt"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if block is None:
            return None
        if cond:
            if cond is None:
                return None
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
        expr: Optional[Optional[AstExpr]], region: er.SourceView
    ) -> Optional["AstReturnStmt"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if expr:
            if expr is None:
                return None
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
    def make(expr: Optional[AstExpr]) -> Optional["AstExprStmt"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if expr is None:
            return None
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
        operator: lx.Token, target: Optional[AstExpr], region: er.SourceView
    ) -> Optional["AstUnaryExpr"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if target is None:
            return None
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
        left: Optional[AstExpr],
        right: Optional[AstExpr],
        region: er.SourceView,
    ) -> Optional["AstBinaryExpr"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if left is None:
            return None
        if right is None:
            return None
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
        function: Optional[AstExpr],
        args: List[Optional[AstExpr]],
        region: er.SourceView,
    ) -> Optional["AstCallExpr"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if function is None:
            return None
        pure_args = []
        for arg in args:
            if arg is None:
                return None
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
    def make(token: Optional[lx.Token]) -> Optional["AstAtomType"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if token is None:
            return None
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
        params: List[Optional[AstType]],
        return_type: Optional[AstType],
        region: er.SourceView,
    ) -> Optional["AstFuncType"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        pure_params = []
        for param in params:
            if param is None:
                return None
            pure_params.append(param)
        if return_type is None:
            return None
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
        target: Optional[AstType], region: er.SourceView
    ) -> Optional["AstOptionalType"]:
        """
        Makes the node or returns an error given its contents with any contained node possibly
        being an error.
        """
        if target is None:
            return None
        return AstOptionalType(target, region)
