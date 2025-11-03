'''
Tree-walking interpreter para model.py
'''

from rich import print  # Usado por el intérprete de ejemplo
from model import * # Importa todas las clases de model.py
from symtab import Symtab # Importa la Tabla de Símbolos


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


class BuiltinFunction:
    '''Wrapper para funciones nativas de Python (built-ins).'''
    def __init__(self, func, arity=-1):
        self.func = func
        self.arity = arity # -1 significa aridad variable

    def __call__(self, interp, *args):
        try:
            return self.func(*args)
        except Exception as e:
            # Propaga errores de la función nativa
            interp.error(None, f"Error en built-in '{self.func.__name__}': {e}")

class Function:

  def __init__(self, node, env):
    self.node = node
    self.env = env

  @property
  def arity(self) -> int:
    return len(self.node.params)

  def __call__(self, interp, *args):

    call_env = Symtab(self.node.name, self.env)

    for param_node, arg_value in zip(self.node.params, args):
        call_env.add(param_node.name, arg_value) # Ej: call_env.add('base', 10)

    result = None 
    try:
      for stmt in self.node.body:
        stmt.accept(interp, call_env) 
        
    except ReturnException as e:
      result = e.value
      
    return result


  def bind(self, instance):
    self.env.add("this", instance)
    return Function(self.node, self.env)

# =====================================================================
# Intérprete Principal
# =====================================================================

class Interpreter(Visitor):
    '''
    Implementación de un intérprete tree-walking usando el Visitor
    definido con 'multimeta' en model.py.
    '''
    def __init__(self):
        self.global_env = Symtab('global')
        self._add_builtins(self.global_env)

    def _add_builtins(self, env: Symtab):
        '''Añade funciones built-in al entorno global.'''

        def builtin_read_int():
            try:
                return int(input())
            except ValueError:
                return 0
        
        def builtin_read_float():
            try:
                return float(input())
            except ValueError:
                return 0.0

        def builtin_read_string():
            return input()

        def builtin_array_length(arr):
            return len(arr)

        builtins = {
            'read_int': BuiltinFunction(builtin_read_int, 0),
            'read_float': BuiltinFunction(builtin_read_float, 0),
            'read_string': BuiltinFunction(builtin_read_string, 0),
            'array_length': BuiltinFunction(builtin_array_length, 1),
        }

        for name, func in builtins.items():
            env.add(name, func)

    def error(self, node, message):
        '''Reporta un error en tiempo de ejecución.'''
        # En un intérprete real, usaríamos la info de línea/columna del nodo
        print(f"[Error de Runtime] {message}")
        raise BminorExit()

    def _check_numeric_operands(self, node, left, right):
        '''Helper para operaciones binarias numéricas.'''
        if isinstance(left, (int, float)) and isinstance(right, (int, float)):
            return True
        
        print (left, right)
        self.error(node, f"En '{node.oper}', los operandos deben ser números (recibido {type(left).__name__} y {type(right).__name__})")

    def _check_numeric_operand(self, node, value):
        '''Helper para operaciones unarias numéricas.'''
        if isinstance(value, (int, float)):
            return True
        self.error(node, f"En '{node.oper}', el operando debe ser un número (recibido {type(value).__name__})")

  


    def interpret(self, node: Node):
        '''Punto de entrada principal para interpretar un AST.'''
        try:
            env = node.accept(self)


            main_func = env.get('main')

            # 3. Si 'main' existe y es una función, llamarla
            if main_func and callable(main_func):
            
                arity = 0
                if hasattr(main_func, 'arity'):
                    arity = main_func.arity
                
                if arity != 0:
                    self.error(None, f"La función 'main' debe definirse sin argumentos (esperado 0, pero tiene {arity})")

      
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
        env = Symtab('global')
        for stmt in node.body:
            stmt.accept(self, env)
        return env

    def visit(self, node: Block, env: Symtab):
     
        for stmt in node.body:
            stmt.accept(self, env)
            
    def visit(self, n: FuncDecl, env: Symtab):
        func_env = Symtab(n.name, env)
        func = Function(n, func_env)
        env.add(n.name, func)

    def visit(self, node: VarDecl, env: Symtab):
        value = None # Valor por defecto

        # Comprobar si es una declaración de array
        if isinstance(node.type, ArrayType):
            if node.type.size:
                # Es un array con tamaño, ej: array [N] boolean
                size_val = node.type.size.accept(self, env)
                
                if not isinstance(size_val, int):
                    self.error(node, f"Tamaño del array '{node.name}' no es un entero (es {type(size_val).__name__})")
                if size_val < 0:
                    self.error(node, f"Tamaño del array '{node.name}' no puede ser negativo ({size_val})")

                # Determinar el valor por defecto para los elementos
                default_elem_val = None
                
                # Necesitamos encontrar el tipo base (puede ser un array de arrays)
                elem_type = node.type.elem_type
                while isinstance(elem_type, ArrayType):
                     elem_type = elem_type.elem_type

                if isinstance(elem_type, SimpleType):
                    if elem_type.name == 'integer':
                        default_elem_val = 0
                    elif elem_type.name == 'float':
                        default_elem_val = 0.0
                    elif elem_type.name == 'boolean':
                        default_elem_val = False # <-- El valor clave para 'isprime'
                    elif elem_type.name == 'string':
                        default_elem_val = ""
                    elif elem_type.name == 'char':
                        default_elem_val = '\0' 
                
                # Asignar una nueva lista (el array) con los valores por defecto
                value = [default_elem_val] * size_val
            else:
                # Es un array sin tamaño (ej: 'array [] boolean' en un parámetro)
                value = None
        
        # Opcional: Asignar valores por defecto a tipos simples también
        elif isinstance(node.type, SimpleType):
            if node.type.name == 'integer': value = 0
            elif node.type.name == 'float': value = 0.0
            elif node.type.name == 'boolean': value = False
            elif node.type.name == 'string': value = ""
            elif node.type.name == 'char': value = '\0'

        env.add(node.name, value)

    def visit(self, node: VarDeclInit, env: Symtab):
        # Declaración con inicializador (potencialmente lista para array)
        if isinstance(node.init, list):
            # Inicialización de array
            value = [item.accept(self, env) for item in node.init]
        elif node.init:
            # Inicialización de variable simple
            value = node.init.accept(self, env)
        else:
            value = None
        env.add(node.name, value)
        
    def visit(self, node: PrintStmt, env):
        value = node.expr.accept(self, env)
        if isinstance(value, str):
            # Interpretar secuencias de escape
            value = value.replace('\\n', '\n').replace('\\t', '\t')
        print(value, end='')

    def visit(self, node: WhileStmt, env: Symtab):
        while _is_truthy(node.cond.accept(self, env)):
            try:
                for stmt in node.body:
                    stmt.accept(self, env)
            except BreakException:
                break # Salir del bucle
            except ContinueException:
                continue # Saltar a la siguiente iteración

    def visit(self, node: DoWhileStmt, env: Symtab):
        while True:
            try:
                node.body.accept(self, env)
            except BreakException:
                break
            except ContinueException:
                # En do-while, 'continue' va a la condición
                pass
            
            if not _is_truthy(node.cond.accept(self, env)):
                break

    def visit(self, node: IfStmt, env: Symtab):
        # return  self.error(node, "División por cero "+str(node.cond.cond));
        cond_val = node.cond.accept(self, env)
        if _is_truthy(cond_val):
            for stmt in node.then_branch:
                stmt.accept(self, env)
        elif node.else_branch:
            for stmt in node.else_branch:
                stmt.accept(self, env)


            
    def visit(self, node: ForStmt, env: Symtab): 
        # 1. Inicializador
        if node.init:
            node.init.accept(self, env)
        
        while True:
            # 2. Condición
            cond_val = True # 'for(;;)' es un bucle infinito
            if node.cond:
                cond_val = node.cond.accept(self, env)
            
            if not _is_truthy(cond_val):
                break # Salir del bucle

            # 3. Cuerpo
            try:
                for stmt in node.body:
                    stmt.accept(self, env)
            except BreakException:
                break # Salir del 'for'
            except ContinueException:
                # 'continue' salta al 'step'
                pass
            
            # 4. Step
            if node.step:
                node.step.accept(self, env)

    def visit(self, node: ReturnStmt, env: Symtab):
        value = None
        if node.expr:
            value = node.expr.accept(self, env)
        raise ReturnException(value)
        
    def visit(self, node: ExprStmt, env: Symtab):
        node.expr.accept(self , env)

    
    def visit(self, node: BinOper, env: Symtab):
        
        # return  self.error(node, "División por cero "+str(node.right.name) + " "  + str(node.lineno));
        left = node.left.accept(self, env)
        right = node.right.accept(self, env)

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

    def visit(self, node: LogicalOpExpr, env: Symtab):
        left = node.left.accept(self, env)
        
        if node.oper == '||':
            # Cortocircuito: si 'left' es verdadero, no evaluar 'right'
            return left if _is_truthy(left) else node.right.accept(self, env)
        elif node.oper == '&&':
            # Cortocircuito: si 'left' es falso, no evaluar 'right'
            return node.right.accept(self, env) if _is_truthy(left) else left
        else:
            raise NotImplementedError(f"Operador lógico no implementado: {node.oper}")

    def visit(self, node: UnaryOper,  env: Symtab):
        expr_val = node.expr.accept(self, env)
        
        if node.oper == '-':
            self._check_numeric_operand(node, expr_val)
            return -expr_val
        elif node.oper == '!':
            return not _is_truthy(expr_val)
        else:
            raise NotImplementedError(f"Operador unario no implementado: {node.oper}")
            
    def visit(self, node: Assign, env: Symtab):
        rvalue = node.right.accept(self, env)
        lvalue_node = node.left
        
        if isinstance(lvalue_node, Identifier):
            # Asignación a variable: x = ...
            env.add(lvalue_node.name, rvalue)
        elif isinstance(lvalue_node, ArrayAccess):
            # Asignación a array: a[i] = ...
            arr = lvalue_node.array.accept(self, env)
            
            idx = lvalue_node.pos.accept(self, env)
            
            if not isinstance(arr, list):
                env.print()
                print(arr, lvalue_node.array.name, lvalue_node.pos )
                self.error(lvalue_node, "Base de acceso a array no es un array " + str(lvalue_node.lineno))
            if not isinstance(idx, int):
                self.error(lvalue_node, "Índice de array no es un entero")
            if idx < 0 or idx >= len(arr):
                self.error(lvalue_node, f"Índice de array fuera de límites ({idx})")
            arr[idx] = rvalue
        else:
            self.error(node, "Target de asignación inválido")
            
        return rvalue # La asignación es una expresión que retorna el rvalue

  
   
        
    def visit(self, node: PreInc, env: Symtab):
        lvalue_node = node.expr
        
        if isinstance(lvalue_node, Identifier):
            name = lvalue_node.name
            value = env.get(name)
            self._check_numeric_operand(node, value)
            value += 1
            env.add(name, value)
            return value
        elif isinstance(lvalue_node, ArrayAccess):
            arr = lvalue_node.array.accept(self, env)
            idx = lvalue_node.index.accept(self, env)
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

    def visit(self, node: PreDec, env: Symtab):
        lvalue_node = node.expr

        if isinstance(lvalue_node, Identifier):
            name = lvalue_node.name
            value = env.get(name)
            self._check_numeric_operand(node, value)
            value -= 1
            env.add(name, value)
            return value
        elif isinstance(lvalue_node, ArrayAccess):
            arr = lvalue_node.array.accept(self, env)
            idx = lvalue_node.index.accept(self, env)
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

    def visit(self, node: Call, env: Symtab):
        callee = node.func.accept(self, env)
        
        if not callable(callee):
            self.error(node, "Intento de llamar a algo que no es una función " + str(node.func.name))
            
        args = [arg.accept(self, env) for arg in node.args]
        
        if hasattr(callee, 'arity') and callee.arity != -1:
            if len(args) != callee.arity:
                self.error(node, f"Error de aridad: Se esperaban {callee.arity} argumentos, pero se recibieron {len(args)}")
        
        return callee(self, *args)
        
    def visit(self, node: ArrayAccess, env: Symtab):
        arr = node.array.accept(self, env)
        idx = node.pos.accept(self, env)
        
        if not isinstance(arr, list):
            self.error(node, "Base de acceso a array no es un array")
        if not isinstance(idx, int):
            self.error(node, "Índice de array no es un entero")
        if idx < 0 or idx >= len(arr):
            self.error(node, f"Índice de array fuera de límites ({idx} para tamaño {len(arr)})")
            
        return arr[idx]

    def visit(self, node: Identifier, env: Symtab):
        # print (node.name)
        # print (env.get(node.name))
        return env.get(node.name)
        
    # =================================================================
    # Visitantes de Nodos (Literales)
    # =================================================================
    
    def visit(self, node: Literal, env: Symtab):
        return node.value

    def visit(self, node: Integer, env: Symtab):
        return node.value

    def visit(self, node: Float, env: Symtab):
        return node.value

    def visit(self, node: Boolean, env: Symtab):
        return node.value

    def visit(self, node: Char, env: Symtab):
        return node.value

    def visit(self, node: String,  env: Symtab):
        return node.value
    
    def visit(self, n: SimpleType, env: Symtab):
        pass
    
    def visit(self, node: Param,  env: Symtab):
        print (node.name, "tipo", node.type, "a")
        node.type.accept(self, env)
        env.add(node.name, node)



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
        print(e)
        # import traceback
        # print(traceback.format_exc())