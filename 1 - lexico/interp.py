'''
Tree-walking interpreter para model.py
'''

from collections import ChainMap
from rich import print  # Usado por el intérprete de ejemplo
from model import * # Importa todas las clases de model.py

# =====================================================================
# Excepciones de Control de Flujo
# =====================================================================

class ReturnException(Exception):
    '''Excepción para manejar la sentencia 'return'.'''
    def __init__(self, value):
        self.value = value

class BreakException(Exception):
    '''Excepción para manejar la sentencia 'break'.'''
    pass

class ContinueException(Exception):
    '''Excepción para manejar la sentencia 'continue'.'''
    pass

class BminorExit(BaseException):
    '''Excepción para detener la ejecución por un error.'''
    pass

def _is_truthy(value):
  '''Define la veracidad de un valor en el lenguaje.'''
  if isinstance(value, bool):
    return value
  if value is None:
    return False
  if isinstance(value, (int, float)):
    return value != 0
  # Todos los demás valores (strings, arrays, funciones) son 'truthy'
  return True



class Function:
    '''Representa una función definida por el usuario (clausura).'''
    def __init__(self, node: FuncDecl, env: ChainMap):
        self.node = node
        self.env = env # El entorno léxico donde se definió la función

    @property
    def arity(self) -> int:
        return len(self.node.params)

    def __call__(self, interp, *args):
        # Crear un nuevo entorno para la ejecución de la función
        # Este entorno tiene como padre el entorno léxico de la función
        newenv = self.env.new_child()

        # Vincular argumentos a parámetros en el nuevo entorno
        for param_node, arg_value in zip(self.node.params, args):
            newenv[param_node.name] = arg_value

        # Guardar el entorno antiguo y activar el nuevo
        oldenv = interp.env
        interp.env = newenv
        result = None

        try:
            # Ejecutar el cuerpo de la función
            for stmt in self.node.body:
                stmt.accept(interp)
        except ReturnException as e:
            result = e.value # Capturar el valor de retorno
        finally:
            # Restaurar el entorno antiguo
            interp.env = oldenv
        
        return result

# =====================================================================
# Intérprete Principal
# =====================================================================

class Interpreter(Visitor):
    '''
    Implementación de un intérprete tree-walking usando el Visitor
    definido con 'multimeta' en model.py.
    '''
    def __init__(self):
        self.env = ChainMap()

    def error(self, node, message):
        '''Reporta un error en tiempo de ejecución.'''
        # En un intérprete real, usaríamos la info de línea/columna del nodo
        print(f"[Error de Runtime] {message}")
        raise BminorExit()

    def _check_numeric_operands(self, node, left, right):
        '''Helper para operaciones binarias numéricas.'''
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return True
        self.error(node, f"En '{node.oper}', los operandos deben ser números (recibido {type(left).__name__} y {type(right).__name__})")

    def _check_numeric_operand(self, node, value):
        '''Helper para operaciones unarias numéricas.'''
        if isinstance(value, (int, float)):
            return True
        self.error(node, f"En '{node.oper}', el operando debe ser un número (recibido {type(value).__name__})")

    def _define(self, name: str, value):
        '''Define una nueva variable en el *entorno actual*.'''
        self.env[name] = value

    def _assign(self, name: str, value):
        '''Asigna un valor a una variable *existente* en el entorno.'''
        for scope in self.env.maps:
            if name in scope:
                scope[name] = value
                return
        self.error(None, f"Asignación a variable no definida '{name}'")
    
    def _lookup(self, name: str):
        '''Busca una variable en los entornos.'''
        try:
            return self.env[name]
        except KeyError:
            self.error(None, f"Variable no definida '{name}'")

    # =================================================================
    # Punto de Entrada
    # =================================================================

    def interpret(self, node: Node):
        '''Punto de entrada principal para interpretar un AST.'''
        try:
            node.accept(self)

            main_func = self.env.get('main')

            # 3. Si 'main' existe y es una función, llamarla
            if main_func and callable(main_func):
                
                # 3a. Verificar que 'main' no requiera argumentos
                # (En un intérprete más complejo, aquí pasaríamos argc/argv)
                arity = 0
                if hasattr(main_func, 'arity'):
                    arity = main_func.arity
                
                if arity != 0:
                    self.error(None, f"La función 'main' debe definirse sin argumentos (esperado 0, pero tiene {arity})")

                # 3b. Llamar a la función 'main'
                # (Recordar que __call__ espera 'self' (el intérprete) 
                # como primer argumento)
                main_func(self)
        except BminorExit:
            pass # Error ya reportado
        except Exception as e:
            print(f"[Error Interno del Intérprete] {e}")
            import traceback
            traceback.print_exc()

    # =================================================================
    # Visitantes de Nodos (Declaraciones y Sentencias)
    # =================================================================

    def visit(self, node: Program):
        for stmt in node.body:
            stmt.accept(self)

    def visit(self, node: Block):
        # Un bloque crea un nuevo entorno léxico
        oldenv = self.env
        self.env = self.env.new_child()
        try:
            for stmt in node.body:
                stmt.accept(self)
        finally:
            # Restaura el entorno anterior al salir del bloque
            self.env = oldenv
            
    def visit(self, node: FuncDecl):
        # Definir la función en el entorno actual
        func = Function(node, self.env)
        self._define(node.name, func)

    def visit(self, node: VarDecl):
        # Declaración de variable (con o sin inicializador)
        value = None
        if node.value:
            value = node.value.accept(self)
        self._define(node.name, value)

    def visit(self, node: VarDeclInit):
        # Declaración con inicializador (potencialmente lista para array)
        if isinstance(node.init, list):
            # Inicialización de array
            value = [item.accept(self) for item in node.init]
        elif node.init:
            # Inicialización de variable simple
            value = node.init.accept(self)
        else:
            value = None
        self._define(node.name, value)
        
    def visit(self, node: PrintStmt):
        value = node.expr.accept(self)
        if isinstance(value, str):
            # Interpretar secuencias de escape
            value = value.replace('\\n', '\n').replace('\\t', '\t')
        print(value, end='')

    def visit(self, node: WhileStmt):
        while _is_truthy(node.cond.accept(self)):
            try:
                node.body.accept(self)
            except BreakException:
                break # Salir del bucle
            except ContinueException:
                continue # Saltar a la siguiente iteración

    def visit(self, node: DoWhileStmt):
        while True:
            try:
                node.body.accept(self)
            except BreakException:
                break
            except ContinueException:
                # En do-while, 'continue' va a la condición
                pass
            
            if not _is_truthy(node.cond.accept(self)):
                break

    def visit(self, node: IfStmt):
        cond_val = node.cond.accept(self)
        if _is_truthy(cond_val):
            for stmt in node.then_branch:
                stmt.accept(self)
        elif node.else_branch:
            for stmt in node.else_branch:
                stmt.accept(self)
            
    def visit(self, node: ForStmt):
        # El 'for' crea su propio entorno
        oldenv = self.env
        self.env = self.env.new_child()
        try:
            # 1. Inicializador
            if node.init:
                node.init.accept(self)
            
            while True:
                # 2. Condición
                cond_val = True # 'for(;;)' es un bucle infinito
                if node.cond:
                    cond_val = node.cond.accept(self)
                
                if not _is_truthy(cond_val):
                    break # Salir del bucle

                # 3. Cuerpo
                try:
                    node.body.accept(self)
                except BreakException:
                    break # Salir del 'for'
                except ContinueException:
                    # 'continue' salta al 'step'
                    pass
                
                # 4. Step
                if node.step:
                    node.step.accept(self)
        finally:
            self.env = oldenv # Restaurar entorno

    def visit(self, node: ReturnStmt):
        value = None
        if node.expr:
            value = node.expr.accept(self)
        raise ReturnException(value)
        
    def visit(self, node: ExprStmt):
        # Ejecuta la expresión por sus efectos secundarios, descarta el valor
        node.expr.accept(self)

    # =================================================================
    # Visitantes de Nodos (Expresiones)
    # =================================================================
    
    def visit(self, node: BinOper):
        left = node.left.accept(self)
        right = node.right.accept(self)

        op = node.oper
        if op == '+':
            # 'add' está sobrecargado para strings
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            self._check_numeric_operands(node, left, right)
            return left + right
        elif op == '-':
            self._check_numeric_operands(node, left, right)
            return left - right
        elif op == '*':
            self._check_numeric_operands(node, left, right)
            return left * right
        elif op == '/':
            self._check_numeric_operands(node, left, right)
            if right == 0:
                self.error(node, "División por cero")
            # Forzar división de flotantes si alguno es flotante
            if isinstance(left, float) or isinstance(right, float):
                return left / right
            else:
                return left // right # División entera
        elif op == '%':
            self._check_numeric_operands(node, left, right)
            if right == 0:
                self.error(node, "Módulo por cero")
            return left % right
        
        # Comparaciones
        elif op == '==': return left == right
        elif op == '!=': return left != right
        elif op == '<':
            self._check_numeric_operands(node, left, right)
            return left < right
        elif op == '>':
            self._check_numeric_operands(node, left, right)
            return left > right
        elif op == '<=':
            self._check_numeric_operands(node, left, right)
            return left <= right
        elif op == '>=':
            self._check_numeric_operands(node, left, right)
            return left >= right
        else:
            raise NotImplementedError(f"Operador binario no implementado: {op}")

    def visit(self, node: LogicalOpExpr):
        left = node.left.accept(self)
        
        if node.oper == '||':
            # Cortocircuito: si 'left' es verdadero, no evaluar 'right'
            return left if _is_truthy(left) else node.right.accept(self)
        elif node.oper == '&&':
            # Cortocircuito: si 'left' es falso, no evaluar 'right'
            return node.right.accept(self) if _is_truthy(left) else left
        else:
            raise NotImplementedError(f"Operador lógico no implementado: {node.oper}")

    def visit(self, node: UnaryOper):
        expr_val = node.expr.accept(self)
        
        if node.oper == '-':
            self._check_numeric_operand(node, expr_val)
            return -expr_val
        elif node.oper == '!':
            return not _is_truthy(expr_val)
        else:
            raise NotImplementedError(f"Operador unario no implementado: {node.oper}")
            
    def visit(self, node: Assign):
        rvalue = node.right.accept(self)
        lvalue_node = node.left
        
        if isinstance(lvalue_node, Identifier):
            # Asignación a variable: x = ...
            self._assign(lvalue_node.name, rvalue)
        elif isinstance(lvalue_node, ArrayAccess):
            # Asignación a array: a[i] = ...
            arr = lvalue_node.array.accept(self)
            idx = lvalue_node.index.accept(self)
            if not isinstance(arr, list):
                self.error(lvalue_node, "Base de acceso a array no es un array")
            if not isinstance(idx, int):
                self.error(lvalue_node, "Índice de array no es un entero")
            if idx < 0 or idx >= len(arr):
                self.error(lvalue_node, f"Índice de array fuera de límites ({idx})")
            arr[idx] = rvalue
        else:
            self.error(node, "Target de asignación inválido")
            
        return rvalue # La asignación es una expresión que retorna el rvalue

    def visit(self, node: PreInc):
        lvalue_node = node.expr
        
        if isinstance(lvalue_node, Identifier):
            name = lvalue_node.name
            value = self._lookup(name)
            self._check_numeric_operand(node, value)
            value += 1
            self._assign(name, value)
            return value
        elif isinstance(lvalue_node, ArrayAccess):
            arr = lvalue_node.array.accept(self)
            idx = lvalue_node.index.accept(self)
            # Validaciones de array/índice
            if not isinstance(arr, list): self.error(lvalue_node, "Base no es array")
            if not isinstance(idx, int): self.error(lvalue_node, "Índice no es entero")
            
            value = arr[idx]
            self._check_numeric_operand(node, value)
            value += 1
            arr[idx] = value
            return value
        else:
            self.error(node, "Operando para '++' debe ser un l-value (variable o acceso a array)")

    def visit(self, node: PreDec):
        lvalue_node = node.expr

        if isinstance(lvalue_node, Identifier):
            name = lvalue_node.name
            value = self._lookup(name)
            self._check_numeric_operand(node, value)
            value -= 1
            self._assign(name, value)
            return value
        elif isinstance(lvalue_node, ArrayAccess):
            arr = lvalue_node.array.accept(self)
            idx = lvalue_node.index.accept(self)
            # Validaciones
            if not isinstance(arr, list): self.error(lvalue_node, "Base no es array")
            if not isinstance(idx, int): self.error(lvalue_node, "Índice no es entero")
            
            value = arr[idx]
            self._check_numeric_operand(node, value)
            value -= 1
            arr[idx] = value
            return value
        else:
            self.error(node, "Operando para '--' debe ser un l-value")

    def visit(self, node: Call):
        callee = node.func.accept(self)
        
        if not callable(callee):
            self.error(node, "Intento de llamar a algo que no es una función")
            
        args = [arg.accept(self) for arg in node.args]
        
        if hasattr(callee, 'arity') and callee.arity != -1:
            if len(args) != callee.arity:
                self.error(node, f"Error de aridad: Se esperaban {callee.arity} argumentos, pero se recibieron {len(args)}")
        
        return callee(self, *args)
        
    def visit(self, node: ArrayAccess):
        arr = node.array.accept(self)
        idx = node.index.accept(self)
        
        if not isinstance(arr, list):
            self.error(node, "Base de acceso a array no es un array")
        if not isinstance(idx, int):
            self.error(node, "Índice de array no es un entero")
        if idx < 0 or idx >= len(arr):
            self.error(node, f"Índice de array fuera de límites ({idx} para tamaño {len(arr)})")
            
        return arr[idx]

    def visit(self, node: Identifier):
        return self._lookup(node.name)
        
    # =================================================================
    # Visitantes de Nodos (Literales)
    # =================================================================
    
    def visit(self, node: Literal):
        return node.value

    def visit(self, node: Integer):
        return node.value

    def visit(self, node: Float):
        return node.value

    def visit(self, node: Boolean):
        return node.value

    def visit(self, node: Char):
        return node.value

    def visit(self, node: String):
        return node.value

    # =================================================================
    # Nodos no visitables (Tipos, etc.)
    # =================================================================
    # No implementamos visit() para:
    # SimpleType, ArrayType, FuncType, Param, IfCond, Declaration
    # ya que son nodos abstractos o de definición de tipos
    # que no se ejecutan en runtime.


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python astprint.py <filename>")
    
    try:
        from parser import parse
        
        # 2. Crear una INSTANCIA del intérprete
        interpreter_instance = Interpreter()
        txt = open(sys.argv[1], encoding='utf-8').read()
        ast = parse(txt)
        # 3. Llamar al método 'interpret' EN LA INSTANCIA
        interpreter_instance.interpret(ast)

    except ImportError:
        print("[red]Error:[/red] No se encontró el archivo 'parser.py'.")
        print("Asegúrate de que tu parser esté implementado y en el mismo directorio.")
    except Exception as e:
        print(f"[red]Ocurrió un error durante el interprete o la impresión:[/red]")
        # print(e)
        # print stack 
        import traceback
        print(traceback.format_exc())