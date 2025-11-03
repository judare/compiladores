# checker.py
'''
Este archivo contiene la parte de verificación de tipos del compilador.
Recorre el AST, construye la tabla de símbolos y valida que los tipos
usados en las operaciones y declaraciones sean consistentes.
'''
from rich    import print
from typing  import Union, List

from errors  import error
from model   import *
from symtab  import Symtab
from typesys import typenames, check_binop, check_unaryop, CheckError, lookup_type


class Check(Visitor):
    @classmethod
    def checker(cls, n: Program):
        checker = cls()
        env = Symtab('global')
        for decl in n.body:
            decl.accept(checker, env)
        return env

    # =====================================================================
    # Declaraciones (crean nuevas entradas en la tabla de símbolos)
    # =====================================================================
    def visit(self, n: VarDecl, env: Symtab):
        '''
        1. Si n.value existe, visitar la expresión para inferir su tipo.
        2. Verificar que el tipo de n.value (si existe) sea asignable al tipo declarado.
        3. Agregar la variable 'n' a la tabla de símbolos actual.
        '''
        n.type.accept(self, env) # Asigna el nombre del tipo a n.type.name
        
        if n.value:
            n.value.accept(self, env)
            if check_binop('=', n.type.name, n.value.type) is None:
                error(f"En asignación de '{n.name}', el tipo '{n.value.type}' no coincide con el tipo declarado '{n.type.name}'", n.lineno)
        
        try:
            env.add(n.name, n)
        except Symtab.SymbolConflictError:
            error(f"La variable '{n.name}' ya fue declarada con un tipo diferente", n.lineno)
        except Symtab.SymbolDefinedError:
            error(f"La variable '{n.name}' ya fue declarada", n.lineno)

    def visit(self, n: FuncDecl, env: Symtab):
        '''
        1. Agregar la función a la tabla de símbolos actual.
        2. Crear una nueva tabla de símbolos para el alcance de la función.
        3. Visitar los parámetros y agregarlos a la nueva tabla.
        4. Visitar el cuerpo de la función.
        '''
        try:
            env.add(n.name, n)
        except Symtab.SymbolConflictError:
            raise CheckError(f"La función '{n.name}' ya fue declarada con un tipo diferente", n.lineno)
        except Symtab.SymbolDefinedError:
            raise CheckError(f"La función '{n.name}' ya fue declarada", n.lineno)
        
        func_env = Symtab(n.name, env)
        for parm in n.params:
            parm.accept(self, func_env)

        for stmt in n.body:
            stmt.accept(self, func_env)

    def visit(self, n: Param, env: Symtab):
        '''
        1. Agregar el parámetro 'n' a la tabla de símbolos actual.
        '''        
        n.type.accept(self, env)
        try:
            env.add(n.name, n)
        except Symtab.SymbolConflictError:
            raise CheckError(f"El parámetro '{n.name}' ya fue declarado con un tipo diferente")
        except Symtab.SymbolDefinedError:
            raise CheckError(f"El parámetro '{n.name}' ya fue declarado")
        except e:
            raise CheckError(f"Error al agregar el parámetro '{n.name}'")
    # =====================================================================
    # Sentencias (Statements)
    # =====================================================================
    def visit(self, n: ReturnStmt, env: Symtab):
        '''
        1. Verificar que el return esté dentro de una función.
        2. Visitar n.expr (si existe) para obtener su tipo.
        3. Verificar que el tipo de n.expr coincida con el tipo de retorno de la función.
        '''
        if env.name == 'global':
            error("La instrucción 'return' no puede estar fuera de una función", n.lineno)
            return

        func = env.get(env.name)
        func.type.accept(self, env)
        expected_type = func.type.name
        
        if n.expr:
            n.expr.accept(self, env)
            if expected_type != n.expr.type:
                error(f"La función '{func.name}' retorna '{expected_type}' pero se encontró un retorno de tipo '{n.expr.type}'", n.lineno)
        elif expected_type != 'void':
             error(f"La función '{func.name}' debe retornar un valor de tipo '{expected_type}'", n.lineno)

    def visit(self, n: Assign, env: Symtab):
        '''
        1. Visitar la parte derecha (right) para obtener su tipo.
        2. Visitar la parte izquierda (left), que debe ser una variable, para obtener su tipo.
        3. Verificar que los tipos sean compatibles para la asignación.
        '''
        n.right.accept(self, env)
        n.left.accept(self, env)
        
        # n.type = check_binop('=', n.left.type, n.right.type)
        # if n.type is None:
        #     error(f"Asignación inválida. No se puede asignar tipo '{n.right.type}' a '{n.left.type}'", n.lineno)

    def visit(self, n: IfStmt, env: Symtab):
        n.cond.accept(self, env)
        if n.cond.type != 'boolean':
            error(f"La condición del 'if' debe ser de tipo 'boolean', no '{n.cond.type}'", n.lineno)
        for stmt in n.then_branch:
            stmt.accept(self, env)
        if n.else_branch:
            for stmt in n.else_branch:
                stmt.accept(self, env)

    def visit(self, n: WhileStmt, env: Symtab):
        n.cond.accept(self, env)
        if n.cond.type != 'boolean':
            error(f"La condición del 'while' debe ser de tipo 'boolean', no '{n.cond.type}'", n.lineno)
        for stmt in n.body:
            stmt.accept(self, env)

    def visit(self, n: DoWhileStmt, env: Symtab):
        # Visita el cuerpo del bucle
        body_stmts = n.body.body if isinstance(n.body, Block) else [n.body]
        for stmt in body_stmts:
            stmt.accept(self, env)
            
        # Visita la condición y verifica que sea booleana
        n.cond.accept(self, env)
        if n.cond.type != 'boolean':
            error(f"La condición del 'do-while' debe ser de tipo 'boolean', no '{n.cond.type}'", n.lineno)

    def visit(self, n: ForStmt, env: Symtab):
        # Visita las tres partes de la cabecera del for
        if n.init:
            n.init.accept(self, env)
        if n.cond:
            n.cond.accept(self, env)
            # if n.cond.type != 'boolean':
            #     error(f"La condición del 'for' debe ser de tipo 'boolean', no '{n.cond.type}'", n.lineno)
        if n.step:
            n.step.accept(self, env)

        # Visita el cuerpo del bucle
        body_stmts = n.body.body if isinstance(n.body, Block) else [n.body]
        for stmt in body_stmts:
            print(stmt)
            # stmt.accept(self, env)

    def visit(self, n: IfCond, env: Symtab):
        # Visita la expresión dentro de la condición
        n.cond.accept(self, env)
        # El tipo del nodo IfCond es el tipo de la expresión que envuelve
        n.type = "boolean" # TODO

    def visit(self, n: ReturnStmt, env: Symtab):
        # 1. Asegurarse de que no esté en el ámbito global
        if env.name == 'global':
            error("La instrucción 'return' no puede estar fuera de una función", n.lineno)
            return

        # 2. Obtener el tipo de retorno esperado de la función actual
        func = env.get(env.name)
        func.type.accept(self, env)
        expected_type = func.type.name
        
        # 3. Comprobar la expresión de retorno
        if n.expr:
            # Caso: return <expression>;
            if expected_type == 'void':
                raise CheckError(f"La función '{func.name}' es de tipo 'void' y no puede retornar un valor")
            
            n.expr.accept(self, env)
            # Comprueba si el tipo retornado coincide con el esperado
            # if n.expr.type != expected_type:
            #     error(f"Tipo de retorno incompatible. La función '{func.name}' esperaba '{expected_type}' pero recibió '{n.expr.type}'", n.lineno)
        else:
            if expected_type != 'void':
                raise CheckError(f"La función '{func.name}' debe retornar un valor de tipo '{expected_type}'")

    def visit(self, n: PrintStmt, env: Symtab):
        if n.expr:
            n.expr.accept(self, env)

    # =====================================================================
    # Expresiones (devuelven un tipo)
    # =====================================================================
    def visit(self, n: BinOper, env: Symtab):
        pass

    def visit(self, n: LogicalOpExpr, env: Symtab):
        pass
        # '''
        # 1. Visitar n.left y n.right para obtener sus tipos.
        # 2. Verificar si n.oper es una operación permitida entre esos tipos.
        # 3. Anotar el tipo resultante en el nodo.
        # '''
        # n.left.accept(self, env)
        # n.right.accept(self, env)
        # n.type = check_binop(n.oper, n.left.type, n.right.type)
        # if n.type is None:
        #     raise SyntaxError(f"Operación inválida '{n.oper}' entre los tipos '{n.left.type}' y '{n.right.type}'")

    def visit(self, n: ExprStmt, env: Symtab):
        n.expr.accept(self, env)

    def visit(self, n: UnaryOper, env: Symtab):
        n.expr.accept(self, env)
        n.type = check_unaryop(n.oper, n.expr.type)
        if n.type is None:
            error(f"Operación unaria inválida '{n.oper}' para el tipo '{n.expr.type}'", n.lineno)

    def visit(self, n: Identifier, env: Symtab):
        '''
        1. Buscar el identificador en la tabla de símbolos.
        2. Si no se encuentra, es un error.
        3. Si se encuentra, obtener su tipo y anotarlo en el nodo.
        '''
        symbol = env.get(n.name)
        if symbol is None:
            n.type = 'undefined' # Para evitar errores en cascada
            raise SyntaxError(f"La variable o función '{n.name}' no está definida")
        else:
            symbol.type.accept(self, env)
            n.type = symbol.type.name

    def visit(self, n: Call, env: Symtab):
        '''
        1. Verificar que la función llamada exista.
        2. Verificar que el número de argumentos coincida.
        3. Verificar que el tipo de cada argumento coincida con el tipo del parámetro.
        4. Anotar el tipo de retorno de la función en el nodo de llamada.
        '''
        func = env.get(n.func.name)
        if not isinstance(func, FuncDecl):
            raise SyntaxError(f"'{n.func.name}' no es una función")

        if len(n.args) != len(func.params):
            raise SyntaxError(f"La función '{func.name}' esperaba {len(func.params)} argumentos, pero recibió {len(n.args)}")
            
        for i, arg in enumerate(n.args):
            arg.accept(self, env)
            param = func.params[i]
            param.type.accept(self, env)
            if arg.type != param.type.name:
                raise SyntaxError(f"En la llamada a '{func.name}', el argumento {i+1} es de tipo '{arg.type}' pero se esperaba '{param.type.name}'")
        
        func.type.accept(self, env)
        n.type = func.type.name

    def visit(self, n: VarDeclInit, env: Symtab):
        env.add(n.name, n)
  

    # =====================================================================
    # Tipos y Literales (casos base de la recursión)
    # =====================================================================
    def visit(self, n: Literal, env: Symtab):
        # El tipo ya está definido en el __post_init__ del nodo Literal
        pass
    
    def visit(self, n: SimpleType, env: Symtab):
        if not lookup_type(n.name):
            raise CheckError(f"El tipo '{n.name}' no está definido.")

    def visit(self, n: ArrayType, env: Symtab):
        # Lógica para verificar arreglos (si se implementa)
        n.elem_type.accept(self, env)
        # if n.size:
        #     if n.size.type != 'integer':
        #         error(f"El tamaño de un arreglo debe ser 'integer', no '{n.size.type}'", n.lineno)



if __name__ == '__main__':
    import sys
    
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python astprint.py <filename>")
    
    try:
        from parser import parse
        txt = open(sys.argv[1], encoding='utf-8').read()
        ast = parse(txt)
        dot = Check.checker(ast)
        # print(ast)
        dot.print();
    except ImportError:
        print("[red]Error:[/red] No se encontró el archivo 'parser.py'.")
        print("Asegúrate de que tu parser esté implementado y en el mismo directorio.")
    except Exception as e:
        print(f"[red]Ocurrió un error durante el parsing o la impresión:[/red]")
        # print(e)
        # print stack 
        import traceback
        print(traceback.format_exc())


