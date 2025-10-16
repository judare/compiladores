# model.py

from dataclasses import dataclass, field
from multimethod import multimeta
from typing      import List, Union

# =====================================================================
# Clases Abstractas
# =====================================================================
class Visitor(metaclass=multimeta):
    pass

@dataclass
class Node:
    def accept(self, v: Visitor, *args, **kwargs):
        return v.visit(self, *args, **kwargs)

@dataclass
class Statement(Node):
    pass

@dataclass
class Expression(Node):
    pass

# =====================================================================
# Definiciones
# =====================================================================
@dataclass
class Program(Statement):
    body: List[Statement] = field(default_factory=list)

@dataclass
class Declaration(Statement):
    pass

@dataclass
class VarDecl(Declaration):
    name : str
    type : Expression
    value: Expression = None

class WhileStmt(Statement):
    def __init__(self, cond, body):
        self.cond = cond
        self.body = body

    def pretty(self, tree=None):
        branch = tree.add("While")
        self.cond.pretty(branch.add("Cond"))
        self.body.pretty(branch.add("Body"))
        return tree

class DoWhileStmt(Statement):
    def __init__(self, body, cond):
        self.body = body
        self.cond = cond

    def pretty(self, tree=None):
        branch = tree.add("DoWhile")
        self.body.pretty(branch.add("Body"))
        self.cond.pretty(branch.add("Cond"))
        return tree

class IfStmt(Node):
    def __init__(self, cond, then_branch, else_branch=None):
        self.cond = cond
        self.then_branch = then_branch
        self.else_branch = else_branch

    def pretty(self, tree=None):
        branch = tree.add("IfStmt")
        if hasattr(self.cond, "pretty"):
            self.cond.pretty(branch)
        else:
            branch.add(f"Cond: {self.cond}")

        branch_then = branch.add("Then")
        if hasattr(self.then_branch, "pretty"):
            self.then_branch.pretty(branch_then)
        else:
            branch_then.add(str(self.then_branch))

        if self.else_branch:
            branch_else = branch.add("Else")
            if hasattr(self.else_branch, "pretty"):
                self.else_branch.pretty(branch_else)
            else:
                branch_else.add(str(self.else_branch))
        return tree

class IfCond(Node):
    def __init__(self, cond):
        self.cond = cond
        self.type = 'boolean'

    def pretty(self, tree=None):
        branch = tree.add("IfCond")
        if self.cond:
            self.cond.pretty(branch.add("Cond"))
        else:
            branch.add("Cond: <empty>")
        return tree

class PreInc(Expression):
    def __init__(self, expr):
        self.expr = expr

    def pretty(self, tree=None):
        branch = tree.add("PreInc")
        self.expr.pretty(branch)
        return tree

class FuncDecl(Node):
    def __init__(self, name, type_func, body=None):
        self.name = name
        self.type_func = type_func
        # FIX: Assign return type from the FuncType node
        self.type = type_func.ret_type
        # FIX: Assign parameters from the FuncType node
        self.params = type_func.params if type_func.params is not None else []
        # FIX: Ensure body is a list
        self.body = body if body is not None else []

    def pretty(self, tree):
        branch = tree.add(f"FuncDecl {self.name}: {self.type.name if hasattr(self.type, 'name') else 'complex type'}")
        params_branch = branch.add("Params")
        for p in self.params:
            p.pretty(params_branch)
        body_branch = branch.add("Body")
        if self.body:
            for stmt in self.body:
                if hasattr(stmt, 'pretty'):
                    stmt.pretty(body_branch)

class Identifier(Node):
    def __init__(self, name):
        self.name = name

    def pretty(self, tree):
        tree.add(f"ID {self.name}")

class Block(Node):
    def __init__(self, body):
        self.body = body

    def pretty(self, tree):
        tree.add("Body")

class PreDec(Expression):
    def __init__(self, expr):
        self.expr = expr

    def pretty(self, tree=None):
        branch = tree.add("PreDec")
        self.expr.pretty(branch)
        return tree

class SimpleType(Node):
    def __init__(self, name):
        self.name = name
        self.type = name

    def pretty(self, tree):
        tree.add(f"Type {self.name}")


class ArrayType(Node):
    def __init__(self, size, elem_type):
        self.name = "array"
        self.size = size      # None si es []
        self.elem_type = elem_type

    def pretty(self, tree):
        branch = tree.add("ArrayType")
        if self.size:
            self.size.pretty(branch.add("Size"))
        self.elem_type.pretty(branch.add("ElementType"))


class FuncType(Node):
    def __init__(self, ret_type, params):
        self.ret_type = ret_type
        self.params = params if params is not None else []

    def pretty(self, tree):
        branch = tree.add("FuncType")
        self.ret_type.pretty(branch.add("ReturnType"))
        params_branch = branch.add("Params")
        for p in self.params:
            p.pretty(params_branch)


class Param(Node):
    def __init__(self, name, typ):
        self.name = name
        self.type = typ

    def pretty(self, tree):
        branch = tree.add(f"Param {self.name}")
        self.type.pretty(branch.add("Type"))

class VarDeclInit(Node):
    def __init__(self, name, typ, init):
        self.name = name
        self.type = typ
        self.init = init
        # Replicate VarDecl structure for checker compatibility
        self.value = init

    def pretty(self, tree):
        branch = tree.add(f"VarDeclInit {self.name}")
        self.type.pretty(branch.add("Type"))
        if isinstance(self.init, list):
            init_branch = branch.add("InitList")
            for e in self.init:
                e.pretty(init_branch)
        else:
            self.init.pretty(branch.add("Init"))

class ReturnStmt(Node):
    def __init__(self, expr):
        self.expr = expr

    def pretty(self, tree):
        branch = tree.add("Return")
        if self.expr: self.expr.pretty(branch)
            
'''
Statement
  |
  +-- Declaration (abstract)
  | |
  | +-- VarDecl: Guardar la información de una declaración de variable
  | |
  | +-- ArrayDecl: Declaración de Arreglos (multi-dimencioanles)
  | |
  | +-- FuncDecl: Para guardar información sobre las funciones declaradas

    -- VarParm
    -- ArrayParm

  -- IfStmt
  -- ReturnStmt
  |
  +-- PrintStmt
  |
  +-- ForStmt
  |
  +-- WhileStmt
  |
  +-- DoWhileStmt
  |
  +-- Assignment
'''
# Expresiones

@dataclass
class BinOper(Expression):
    oper : str
    left : Expression
    right: Expression

@dataclass
class UnaryOper(Expression):
    oper : str
    expr : Expression

@dataclass
class Literal(Expression):
    value : Union[int, float, str, bool]
    type  : str = None

@dataclass
class Integer(Literal):
    value : int

    def __post_init__(self):
        assert isinstance(self.value, int), "Value debe ser un 'integer'"
        self.type = 'integer'

@dataclass
class Float(Literal):
    value : float

    def __post_init__(self):
        assert isinstance(self.value, float), "Value debe ser un 'float'"
        self.type = 'float'

@dataclass
class Boolean(Literal):
    value : bool

    def __post_init__(self):
        assert isinstance(self.value, bool), "Value debe ser un 'boolean'"
        self.type = 'boolean'


class Assign(Node):
    def __init__(self, left, right):
        self.left = left
        self.right = right
    def pretty(self, tree):
        branch = tree.add("Assign")
        self.left.pretty(branch.add("Left"))
        self.right.pretty(branch.add("Right"))

class Call(Node):
    def __init__(self, func, args):
        self.func = func
        self.args = args
    def pretty(self, tree):
        branch = tree.add("Call")
        self.func.pretty(branch.add("Func"))
        for a in self.args:
            a.pretty(branch.add("Arg"))

class ArrayAccess(Node):
    def __init__(self, array, index):
        self.array = array
        self.index = index
    def pretty(self, tree):
        branch = tree.add("ArrayAccess")
        self.array.pretty(branch.add("Array"))
        self.index.pretty(branch.add("Index"))

@dataclass
class Char(Literal):
    value: str

    def __post_init__(self):
        assert isinstance(self.value, str), "Value must be a 'str'"
        self.type = 'char'
    
    def pretty(self, tree):
        tree.add(f"Char {self.value}")

@dataclass
class String(Literal):
    value: str

    def __post_init__(self):
        assert isinstance(self.value, str), "Value must be a 'str'"
        self.type = 'string'

    def pretty(self, tree):
        tree.add(f"String {self.value}")


class ForStmt(Node):
    def __init__(self, init, cond, step, body):
        self.init = init
        self.cond = cond
        self.step = step
        self.body = body

    def pretty(self, tree):
        branch = tree.add("For")
        if self.init: self.init.pretty(branch.add("Init"))
        if self.cond: self.cond.pretty(branch.add("Cond"))
        if self.step: self.step.pretty(branch.add("Step"))
        self.body.pretty(branch.add("Body"))


@dataclass
class PrintStmt(Statement):
    expr: Expression