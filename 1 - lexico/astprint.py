from graphviz import Digraph
from rich     import print
from model    import *


class ASTPrinter(Visitor):
    node_defaults = {
        'shape' : 'box',
        'color' : 'deepskyblue',
        'style' : 'filled'
    }
    edge_defaults = {
        'arrowhead' : 'none'
    }
    def __init__(self):
        self.dot = Digraph('AST')
        self.dot.attr('node', **self.node_defaults)
        self.dot.attr('edge', **self.edge_defaults)
        self._seq = 0
    
    @property
    def name(self):
        self._seq += 1
        return f'n{self._seq:02d}'
    
    @classmethod
    def render(cls, n: Node):
        dot = cls()
        n.accept(dot)
        return dot.dot

    # =====================================================================
    # Nodos Estructurales y Declaraciones
    # =====================================================================

    def visit(self, n: Program):
        name = self.name
        self.dot.node(name, label='Program')
        for stmt in n.body:
            self.dot.edge(name, stmt.accept(self))
        return name

    def visit(self, n: VarDecl):
        name = self.name
        self.dot.node(name, label=f'VarDecl\n{n.name}:{n.type}')
        if n.value:
            self.dot.edge(name, n.value.accept(self))
        return name
        
    def visit(self, n: FuncDecl):
        name = self.name
        # Extraer nombres de parámetros para una mejor visualización
        param_names = ', '.join([p.name for p in n.type_func.params])
        self.dot.node(name, label=f'FuncDecl\n{n.name}({param_names}) : {n.type_func.ret_type.name}')
        
        # CORRECCIÓN AQUÍ: Iterar sobre el cuerpo si es una lista.
        if n.body:
            for stmt in n.body:
                self.dot.edge(name, stmt.accept(self))
        return name
        
    def visit(self, n: Block):
        name = self.name
        self.dot.node(name, label='Block')
        for stmt in n.body:
            self.dot.edge(name, stmt.accept(self))
        return name

    # =====================================================================
    # Nodos de Sentencias de Control
    # =====================================================================
    
    def visit(self, n: IfStmt):
        name = self.name
        self.dot.node(name, label='If')
        self.dot.edge(name, n.cond.accept(self), label='cond')
        self.dot.edge(name, n.then_branch.accept(self), label='then')
        if n.else_branch:
            self.dot.edge(name, n.else_branch.accept(self), label='else')
        return name

    def visit(self, n: WhileStmt):
        name = self.name
        self.dot.node(name, label='While')
        self.dot.edge(name, n.cond.accept(self), label='cond')
        self.dot.edge(name, n.body.accept(self), label='body')
        return name

    def visit(self, n: ForStmt):
        name = self.name
        self.dot.node(name, label='For')
        if n.init:
            self.dot.edge(name, n.init.accept(self), label='init')
        if n.cond:
            self.dot.edge(name, n.cond.accept(self), label='cond')
        if n.step:
            self.dot.edge(name, n.step.accept(self), label='step')
        self.dot.edge(name, n.body.accept(self), label='body')
        return name
        
    def visit(self, n: ReturnStmt):
        name = self.name
        self.dot.node(name, label='Return')
        if n.expr:
            self.dot.edge(name, n.expr.accept(self))
        return name

    # =====================================================================
    # Nodos de Expresiones
    # =====================================================================
    
    def visit(self, n: BinOper):
        name = self.name
        self.dot.node(name, label=f'{n.oper}', shape='circle')
        self.dot.edge(name, n.left.accept(self))
        self.dot.edge(name, n.right.accept(self))
        return name

    def visit(self, n: UnaryOper):
        name = self.name
        self.dot.node(name, label=f'{n.oper}', shape='circle')
        self.dot.edge(name, n.expr.accept(self))
        return name
        
    def visit(self, n: Assign):
        name = self.name
        self.dot.node(name, label='=', shape='circle')
        self.dot.edge(name, n.left.accept(self))
        self.dot.edge(name, n.right.accept(self))
        return name

    def visit(self, n: Call):
        name = self.name
        self.dot.node(name, label='Call')
        self.dot.edge(name, n.func.accept(self), label='func')
        for arg in n.args:
            self.dot.edge(name, arg.accept(self), label='arg')
        return name
        
    def visit(self, n: ArrayAccess):
        name = self.name
        self.dot.node(name, label='[]')
        self.dot.edge(name, n.array.accept(self), label='array')
        self.dot.edge(name, n.index.accept(self), label='index')
        return name
        
    def visit(self, n: PrintStmt):
        name = self.name
        self.dot.node(name, label='Print')
        if n.expr:
            self.dot.edge(name, n.expr.accept(self))
        return name

    # =====================================================================
    # Nodos Hoja (Literales e Identificadores)
    # =====================================================================

    def visit(self, n: Literal):
        name = self.name
        self.dot.node(name, label=f'{n.value}:{n.type}')
        return name

    def visit(self, n: Identifier):
        name = self.name
        self.dot.node(name, label=f'ID({n.name})')
        return name
        
    def visit(self, n: String):
        name = self.name
        self.dot.node(name, label=f'"{n.value}"')
        return name

    def visit(self, n: Char):
        name = self.name
        self.dot.node(name, label=f"'{n.value}'")
        return name


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python astprint.py <filename>")
    
    try:
        from parser import parse
        txt = open(sys.argv[1], encoding='utf-8').read()
        ast = parse(txt)
        dot = ASTPrinter.render(ast)
        print(dot)
    except ImportError:
        print("[red]Error:[/red] No se encontró el archivo 'parser.py'.")
        print("Asegúrate de que tu parser esté implementado y en el mismo directorio.")
    except Exception as e:
        print(f"[red]Ocurrió un error durante el parsing o la impresión:[/red]")
        print(e)