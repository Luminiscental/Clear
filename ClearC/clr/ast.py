"""
Module containing definitions for a Clear ast and a base class for ast visitors.
"""

from typing import Union, List, Optional, Tuple, Dict, Iterable

import dataclasses as dc

import clr.errors as er
import clr.lexer as lx
import clr.annotations as an
import clr.types as ts
import clr.bytecode as bc

# Visitor definitions:


class AstVisitor:
    """
    Base class for an ast visitor.
    """

    def __init__(self) -> None:
        self.errors = er.ErrorTracker()

    def start(self, node: "Ast") -> None:
        """
        Start visiting a tree.
        """

    def binding(self, node: "AstBinding") -> None:
        """
        Visit a value binding node.
        """

    def param(self, node: "AstParam") -> None:
        """
        Visit a parameter declaration node.
        """

    def struct_decl(self, node: "AstStructDecl") -> None:
        """
        Visit a struct declaration node.
        """

    def value_decl(self, node: "AstValueDecl") -> None:
        """
        Visit a value declaration node.
        """

    def func_decl(self, node: "AstFuncDecl") -> None:
        """
        Visit a function declaration node.
        """

    def print_stmt(self, node: "AstPrintStmt") -> None:
        """
        Visit a print statement node.
        """

    def block_stmt(self, node: "AstBlockStmt") -> None:
        """
        Visit a block statement node.
        """

    def set_stmt(self, node: "AstSetStmt") -> None:
        """
        Visit a set statement node.
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

    def nil_expr(self, node: "AstNilExpr") -> None:
        """
        Visit a nil literal.
        """

    def case_expr(self, node: "AstCaseExpr") -> None:
        """
        Visit a case expression.
        """

    def call_expr(self, node: "AstCallExpr") -> None:
        """
        Visit a function call expression node.
        """

    def tuple_expr(self, node: "AstTupleExpr") -> None:
        """
        Visit a tuple expression node.
        """

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        """
        Visit a lambda expression.
        """

    def construct_expr(self, node: "AstConstructExpr") -> None:
        """
        Visit a construct expression.
        """

    def access_expr(self, node: "AstAccessExpr") -> None:
        """
        Visit an access expression.
        """

    def ident_type(self, node: "AstIdentType") -> None:
        """
        Visit an identifier type node.
        """

    def void_type(self, node: "AstVoidType") -> None:
        """
        Visit a void type node.
        """

    def func_type(self, node: "AstFuncType") -> None:
        """
        Visit a function type node.
        """

    def optional_type(self, node: "AstOptionalType") -> None:
        """
        Visit an optional type node.
        """

    def union_type(self, node: "AstUnionType") -> None:
        """
        Visit a union type node.
        """

    def tuple_type(self, node: "AstTupleType") -> None:
        """
        Visit a tuple type node.
        """


class DeepVisitor(AstVisitor):
    """
    Ast visitor that propogates to all nodes for a convenient base class.
    """

    def _decl(self, node: "AstDecl") -> None:
        pass

    def start(self, node: "Ast") -> None:
        for decl in node.decls:
            decl.accept(self)

    def param(self, node: "AstParam") -> None:
        node.param_type.accept(self)
        node.binding.accept(self)

    def struct_decl(self, node: "AstStructDecl") -> None:
        for param in node.params:
            param.accept(self)
        for generator, _ in node.generators:
            generator.accept(self)
        self._decl(node)

    def value_decl(self, node: "AstValueDecl") -> None:
        for decorator in node.decorators:
            decorator.accept(self)
        for binding in node.bindings:
            binding.accept(self)
        if node.val_type:
            node.val_type.accept(self)
        node.val_init.accept(self)
        self._decl(node)

    def func_decl(self, node: "AstFuncDecl") -> None:
        for decorator in node.decorators:
            decorator.accept(self)
        node.binding.accept(self)
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)
        node.block.accept(self)
        self._decl(node)

    def print_stmt(self, node: "AstPrintStmt") -> None:
        if node.expr:
            node.expr.accept(self)
        self._decl(node)

    def block_stmt(self, node: "AstBlockStmt") -> None:
        for decl in node.decls:
            decl.accept(self)
        self._decl(node)

    def set_stmt(self, node: "AstSetStmt") -> None:
        node.target.accept(self)
        node.value.accept(self)
        self._decl(node)

    def if_stmt(self, node: "AstIfStmt") -> None:
        node.if_part[0].accept(self)
        node.if_part[1].accept(self)
        for cond, block in node.elif_parts:
            cond.accept(self)
            block.accept(self)
        if node.else_part:
            node.else_part.accept(self)
        self._decl(node)

    def while_stmt(self, node: "AstWhileStmt") -> None:
        if node.cond:
            node.cond.accept(self)
        node.block.accept(self)
        self._decl(node)

    def return_stmt(self, node: "AstReturnStmt") -> None:
        if node.expr:
            node.expr.accept(self)
        self._decl(node)

    def expr_stmt(self, node: "AstExprStmt") -> None:
        node.expr.accept(self)
        self._decl(node)

    def unary_expr(self, node: "AstUnaryExpr") -> None:
        node.target.accept(self)

    def binary_expr(self, node: "AstBinaryExpr") -> None:
        node.left.accept(self)
        node.right.accept(self)

    def case_expr(self, node: "AstCaseExpr") -> None:
        node.target.accept(self)
        node.binding.accept(self)
        for case_type, case_value in node.cases:
            case_type.accept(self)
            case_value.accept(self)
        if node.fallback:
            node.fallback.accept(self)

    def call_expr(self, node: "AstCallExpr") -> None:
        node.function.accept(self)
        for arg in node.args:
            arg.accept(self)

    def tuple_expr(self, node: "AstTupleExpr") -> None:
        for expr in node.exprs:
            expr.accept(self)

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        for param in node.params:
            param.accept(self)
        node.value.accept(self)

    def construct_expr(self, node: "AstConstructExpr") -> None:
        for label, value in node.inits:
            label.accept(self)
            value.accept(self)

    def access_expr(self, node: "AstAccessExpr") -> None:
        node.target.accept(self)

    def func_type(self, node: "AstFuncType") -> None:
        for param in node.params:
            param.accept(self)
        node.return_type.accept(self)

    def optional_type(self, node: "AstOptionalType") -> None:
        node.target.accept(self)

    def union_type(self, node: "AstUnionType") -> None:
        for subtype in node.types:
            subtype.accept(self)

    def tuple_type(self, node: "AstTupleType") -> None:
        for subtype in node.types:
            subtype.accept(self)


AstContext = Union[
    "AstScope", "AstStructDecl", "AstFuncDecl", "AstIfStmt", "AstWhileStmt"
]


class ContextVisitor(DeepVisitor):
    """
    Ast visitor base class to keep track of the current scope, function and struct.
    """

    def __init__(self) -> None:
        super().__init__()
        self._contexts: List[AstContext] = []

    def _push_context(self, context: AstContext) -> None:
        self._contexts.append(context)

    def _get_context(self) -> AstContext:
        return self._contexts[-1]

    def _pop_context(self) -> AstContext:
        return self._contexts.pop()

    def _get_struct(self) -> Optional["AstStructDecl"]:
        for context in reversed(self._contexts):
            if isinstance(context, AstStructDecl):
                return context
        return None

    def start(self, node: "Ast") -> None:
        self._push_context(node)
        super().start(node)
        self._pop_context()

    def struct_decl(self, node: "AstStructDecl") -> None:
        self._push_context(node)
        for param in node.params:
            param.accept(self)
        for generator, _ in node.generators:
            generator.accept(self)
        self._pop_context()
        self._decl(node)

    def func_decl(self, node: "AstFuncDecl") -> None:
        for decorator in node.decorators:
            decorator.accept(self)
        node.binding.accept(self)
        node.return_type.accept(self)
        self._push_context(node)
        for param in node.params:
            param.accept(self)
        for decl in node.block.decls:
            decl.accept(self)
        self._pop_context()
        self._decl(node)

    def block_stmt(self, node: "AstBlockStmt") -> None:
        self._push_context(node)
        for decl in node.decls:
            decl.accept(self)
        self._pop_context()
        self._decl(node)

    def if_stmt(self, node: "AstIfStmt") -> None:
        self._push_context(node)
        node.if_part[0].accept(self)
        node.if_part[1].accept(self)
        for cond, block in node.elif_parts:
            cond.accept(self)
            block.accept(self)
        if node.else_part:
            node.else_part.accept(self)
        self._pop_context()
        self._decl(node)

    def while_stmt(self, node: "AstWhileStmt") -> None:
        self._push_context(node)
        if node.cond:
            node.cond.accept(self)
        node.block.accept(self)
        self._pop_context()
        self._decl(node)

    def case_expr(self, node: "AstCaseExpr") -> None:
        node.target.accept(self)
        self._push_context(node)
        node.binding.accept(self)
        for case_type, case_value in node.cases:
            case_type.accept(self)
            case_value.accept(self)
        if node.fallback:
            node.fallback.accept(self)
        self._pop_context()

    def lambda_expr(self, node: "AstLambdaExpr") -> None:
        self._push_context(node)
        super().lambda_expr(node)
        self._pop_context()


# Node definitions:

# Base node types:


@dc.dataclass(eq=False, repr=False)
class AstNode:
    """
    Base class for an ast node. All nodes must be able to accept an ast visitor.
    """

    region: er.SourceView = er.SourceView.all("")

    def accept(self, visitor: AstVisitor) -> None:
        """
        Accept a visitor to this node, calling the relevant method of the visitor.
        """


@dc.dataclass(eq=False, repr=False)
class AstTyped(AstNode):
    """
    Base class for nodes with type annotations.
    """

    type_annot = ts.UNRESOLVED


@dc.dataclass(eq=False, repr=False)
class AstIndexed(AstNode):
    """
    Base class for nodes with index annotations.
    """

    index_annot = an.IndexAnnot(value=-1, kind=an.IndexAnnotType.UNRESOLVED)


class AstType(AstTyped):
    """
    Base class for types to help mypy.
    """


class AstExpr(AstTyped):
    """
    Base class for expressions to help mypy.
    """


AstName = Union["AstBinding", "AstStructDecl"]


@dc.dataclass(eq=False, repr=False)
class AstScope(AstNode):
    """
    Base class for a node with scope.
    """

    names: Dict[str, AstName] = dc.field(default_factory=dict)


@dc.dataclass(eq=False, repr=False)
class AstFunction(AstNode):
    """
    Base class for a function node.
    """

    params: List["AstParam"] = dc.field(default_factory=list)
    upvalues: List["AstBinding"] = dc.field(default_factory=list)
    upvalue_indices: List[an.IndexAnnot] = dc.field(default_factory=list)


@dc.dataclass(eq=False, repr=False)
class AstDecl(AstNode):
    """
    Base class for declarations, annotated with return possibilities and scope.
    """

    return_annot = an.ReturnAnnot.NEVER
    scope: Optional[AstScope] = None
    context: Optional[AstContext] = None


AstStmt = Union[
    "AstPrintStmt",
    "AstSetStmt",
    "AstBlockStmt",
    "AstIfStmt",
    "AstWhileStmt",
    "AstReturnStmt",
    "AstExprStmt",
]


@dc.dataclass(eq=False, repr=False)
class AstNameDecl(AstDecl):
    """
    Base class for name declarations, annotated with possible decorators.
    """

    decorators: List[AstExpr] = dc.field(default_factory=list)


# Specific nodes:


@dc.dataclass(eq=False, repr=False)
class Ast(AstScope):
    """
    The root ast node.
    """

    decls: List[AstDecl] = dc.field(default_factory=list)
    # Annotations:
    sequence: List[AstDecl] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.start(self)


@dc.dataclass(eq=False, repr=False)
class AstBinding(AstTyped, AstIndexed):
    """
    Ast node for a value binding.
    """

    name: str = ""
    # Annotations:
    dependency: Optional[AstNameDecl] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.binding(self)


class AstParam(AstNode):
    """
    Ast node for a parameter declaration.
    """

    def __init__(self, param_type: AstType, binding: AstBinding) -> None:
        super().__init__(region=er.SourceView.range(param_type.region, binding.region))
        self.param_type = param_type
        self.binding = binding

    def accept(self, visitor: AstVisitor) -> None:
        visitor.param(self)


@dc.dataclass(eq=False, repr=False)
class AstBlockStmt(AstDecl, AstScope):
    """
    Ast node for a block statement.
    """

    decls: List[AstDecl] = dc.field(default_factory=list)
    # Annotations:
    sequence: List[AstDecl] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.block_stmt(self)


class AstStructDecl(AstDecl, AstTyped):
    """
    Ast node for a struct declaration.
    """

    def __init__(
        self,
        name: str,
        fields: List[Union[AstParam, AstNameDecl]],
        region: er.SourceView,
    ) -> None:
        super().__init__(region=region)
        self.name = name
        self.params = [field for field in fields if isinstance(field, AstParam)]
        self.generators: List[Tuple["AstFuncDecl", List["AstBinding"]]] = []
        for field in fields:
            if isinstance(field, AstParam):
                continue
            decls: List[AstDecl] = [field]
            if isinstance(field, AstValueDecl):
                if len(field.bindings) == 1:
                    expr: AstExpr = AstIdentExpr(name=field.bindings[0].name)
                else:
                    expr = AstTupleExpr(
                        exprs=[
                            AstIdentExpr(name=binding.name)
                            for binding in field.bindings
                        ]
                    )
                decls.append(AstReturnStmt(expr=expr))
                bindings = field.bindings
            elif isinstance(field, AstFuncDecl):
                decls.append(AstReturnStmt(expr=AstIdentExpr(name=field.binding.name)))
                bindings = [field.binding]
            params = [
                AstParam(
                    param_type=AstIdentType(name=self.name),
                    binding=AstBinding(name="this"),
                )
            ]
            self.generators.append(
                (AstFuncDecl(params=params, block=AstBlockStmt(decls=decls)), bindings)
            )
        # Annotations:
        self.indices: List[an.IndexAnnot] = []
        self.sequence: List["AstFuncDecl"] = []

    def iter_bindings(self) -> Iterable[AstBinding]:
        """
        Iterate over all the field bindings of the struct.
        """
        for param in self.params:
            yield param.binding
        for _, bindings in self.generators:
            for binding in bindings:
                yield binding

    def accept(self, visitor: AstVisitor) -> None:
        visitor.struct_decl(self)


@dc.dataclass(eq=False, repr=False)
class AstValueDecl(AstNameDecl, AstTyped):
    """
    Ast node for a value declaration.
    """

    bindings: List[AstBinding] = dc.field(default_factory=list)
    val_type: Optional[AstType] = None
    val_init: AstExpr = dc.field(default_factory=AstExpr)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.value_decl(self)


@dc.dataclass(eq=False, repr=False)
class AstFuncDecl(AstNameDecl, AstFunction, AstTyped):
    """
    Ast node for a function declaration.
    """

    binding: AstBinding = dc.field(default_factory=AstBinding)
    params: List[AstParam] = dc.field(default_factory=list)
    return_type: AstType = dc.field(default_factory=AstType)
    block: "AstBlockStmt" = dc.field(default_factory=AstBlockStmt)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.func_decl(self)


@dc.dataclass(eq=False, repr=False)
class AstPrintStmt(AstDecl):
    """
    Ast node for a print statement.
    """

    expr: Optional[AstExpr] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.print_stmt(self)


@dc.dataclass(eq=False, repr=False)
class AstIfStmt(AstDecl):
    """
    Ast node for an if statement.
    """

    if_part: Tuple[AstExpr, AstBlockStmt] = dc.field(
        default_factory=lambda: (AstExpr(), AstBlockStmt())
    )
    elif_parts: List[Tuple[AstExpr, AstBlockStmt]] = dc.field(default_factory=list)
    else_part: Optional[AstBlockStmt] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.if_stmt(self)


@dc.dataclass(eq=False, repr=False)
class AstWhileStmt(AstDecl):
    """
    Ast node for a while statement.
    """

    cond: Optional[AstExpr] = None
    block: AstBlockStmt = dc.field(default_factory=AstBlockStmt)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.while_stmt(self)


@dc.dataclass(eq=False, repr=False)
class AstReturnStmt(AstDecl):
    """
    Ast node for a return statement.
    """

    expr: Optional[AstExpr] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.return_stmt(self)


@dc.dataclass(eq=False, repr=False)
class AstExprStmt(AstDecl):
    """
    Ast node for an expression statement.
    """

    expr: AstExpr = dc.field(default_factory=AstExpr)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.expr_stmt(self)


@dc.dataclass(eq=False, repr=False)
class AstUnaryExpr(AstExpr):
    """
    Ast node for a unary expression.
    """

    operator: lx.Token = lx.Token(kind=lx.TokenType.ERROR, lexeme=er.SourceView.all(""))
    target: AstExpr = dc.field(default_factory=AstExpr)
    # Annotations:
    opcodes: List[bc.Instruction] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.unary_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstBinaryExpr(AstExpr):
    """
    Ast node for a binary expression.
    """

    operator: lx.Token = lx.Token(kind=lx.TokenType.ERROR, lexeme=er.SourceView.all(""))
    left: AstExpr = dc.field(default_factory=AstExpr)
    right: AstExpr = dc.field(default_factory=AstExpr)
    # Annotations:
    opcodes: List[bc.Instruction] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.binary_expr(self)


class AstIntExpr(AstExpr):
    """
    Ast node for an int literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(region=literal.lexeme)
        self.literal = str(literal)
        self.value = int(self.literal[:-1])

    def accept(self, visitor: AstVisitor) -> None:
        visitor.int_expr(self)


class AstNumExpr(AstExpr):
    """
    Ast node for a num literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(region=literal.lexeme)
        self.literal = str(literal)
        self.value = float(self.literal)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.num_expr(self)


class AstStrExpr(AstExpr):
    """
    Ast node for a str literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(region=literal.lexeme)
        self.literal = str(literal)
        self.value = self.literal[1:-1]

    def accept(self, visitor: AstVisitor) -> None:
        visitor.str_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstIdentExpr(AstExpr, AstIndexed):
    """
    Ast node for an identifier expression.
    """

    name: str = ""
    # Annotations:
    ref: Optional[AstBinding] = None
    struct: Optional[AstStructDecl] = None

    @staticmethod
    def make(token: lx.Token) -> "AstIdentExpr":
        """
        Make an identifer expression node from a token.
        """
        return AstIdentExpr(name=str(token), region=token.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.ident_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstSetStmt(AstDecl):
    """
    Ast node for a set statement.
    """

    target: AstIdentExpr = dc.field(default_factory=AstIdentExpr)
    value: AstExpr = dc.field(default_factory=AstExpr)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.set_stmt(self)


class AstBoolExpr(AstExpr):
    """
    Ast node for a boolean expression.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(region=literal.lexeme)
        self.value = str(literal) == "true"

    def accept(self, visitor: AstVisitor) -> None:
        visitor.bool_expr(self)


class AstNilExpr(AstExpr):
    """
    Ast node for a nil literal.
    """

    def __init__(self, literal: lx.Token) -> None:
        super().__init__(region=literal.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.nil_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstCaseExpr(AstExpr, AstScope):
    """
    Ast node for a case expression.
    """

    target: AstExpr = dc.field(default_factory=AstExpr)
    binding: AstBinding = dc.field(default_factory=AstBinding)
    cases: List[Tuple[AstType, AstExpr]] = dc.field(default_factory=list)
    fallback: Optional[AstExpr] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.case_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstCallExpr(AstExpr):
    """
    Ast node for a function call expression.
    """

    function: AstExpr = dc.field(default_factory=AstExpr)
    args: List[AstExpr] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.call_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstTupleExpr(AstExpr):
    """
    Ast node for a tuple expression.
    """

    exprs: List[AstExpr] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.tuple_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstLambdaExpr(AstExpr, AstScope, AstFunction):
    """
    Ast node for a lambda expression.
    """

    params: List[AstParam] = dc.field(default_factory=list)
    value: AstExpr = dc.field(default_factory=AstExpr)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.lambda_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstLabel(AstNode):
    """
    Ast node for an identifier with no extra meaning.
    """

    name: str = ""

    @staticmethod
    def make(token: lx.Token) -> "AstLabel":
        """
        Make a label node from an identifier token.
        """
        return AstLabel(name=str(token), region=token.lexeme)


@dc.dataclass(eq=False, repr=False)
class AstConstructExpr(AstExpr, AstIndexed):
    """
    Ast node for a construct expression.
    """

    name: str = ""
    inits: List[Tuple[AstLabel, AstExpr]] = dc.field(default_factory=list)
    # Annotations:
    ref: Optional[AstStructDecl] = None
    inside: bool = False

    def get_dict(self) -> Dict[str, AstExpr]:
        """
        Return a dictionary of field name to value.
        """
        return {label.name: value for label, value in self.inits}

    def accept(self, visitor: AstVisitor) -> None:
        visitor.construct_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstAccessExpr(AstExpr):
    """
    Ast node for an access expression.
    """

    target: AstExpr = dc.field(default_factory=AstExpr)
    name: str = ""
    # Annotations:
    ref: Optional[AstStructDecl] = None

    def accept(self, visitor: AstVisitor) -> None:
        visitor.access_expr(self)


@dc.dataclass(eq=False, repr=False)
class AstIdentType(AstType):
    """
    Ast node for an atomic type.
    """

    name: str = ""
    # Annotations
    ref: Optional[AstStructDecl] = None

    @staticmethod
    def make(token: lx.Token) -> "AstIdentType":
        """
        Make an identifer type node from a token.
        """
        return AstIdentType(name=str(token), region=token.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.ident_type(self)


class AstVoidType(AstType):
    """
    Ast node for a void type.
    """

    def __init__(self, token: lx.Token) -> None:
        super().__init__(region=token.lexeme)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.void_type(self)


@dc.dataclass(eq=False, repr=False)
class AstFuncType(AstType):
    """
    Ast node for a function type.
    """

    params: List[AstType] = dc.field(default_factory=list)
    return_type: AstType = dc.field(default_factory=AstType)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.func_type(self)


@dc.dataclass(eq=False, repr=False)
class AstOptionalType(AstType):
    """
    Ast node for an optional type.
    """

    target: AstType = dc.field(default_factory=AstType)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.optional_type(self)


@dc.dataclass(eq=False, repr=False)
class AstUnionType(AstType):
    """
    Ast node for a union type.
    """

    types: List[AstType] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.union_type(self)


@dc.dataclass(eq=False, repr=False)
class AstTupleType(AstType):
    """
    Ast node for a tuple type.
    """

    types: List[AstType] = dc.field(default_factory=list)

    def accept(self, visitor: AstVisitor) -> None:
        visitor.tuple_type(self)
