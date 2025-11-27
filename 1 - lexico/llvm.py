

from llvmlite import ir
import llvmlite.binding as llvm
from model import * 

int_type   = ir.IntType(32)
float_type = ir.DoubleType()
bool_type  = ir.IntType(1)
char_type  = ir.IntType(8)
void_type  = ir.VoidType()
string_type = ir.IntType(8).as_pointer() # char*

class LLVMGenerator(Visitor):
    def __init__(self):
        self.module = ir.Module('bminor_module')
    
        llvm.initialize_native_target()
        llvm.initialize_native_asmprinter()
        
        self.module.triple = llvm.get_default_triple()        
        self.builder = None
        self.function = None
        self.str_counter = 0 
        
        self.scopes = [{}] 
        self.loop_stack = [] 

        self._setup_runtime()
        
    def _setup_runtime(self):
        # int printf(char*, ...)
        printf_ty = ir.FunctionType(int_type, [char_type.as_pointer()], var_arg=True)
        self.printf = ir.Function(self.module, printf_ty, name="printf")
        
        # Strings de formato globales
        self.fmt_int   = self._create_global_string("%d\n", "fmt_int")
        self.fmt_float = self._create_global_string("%f\n", "fmt_float")
        self.fmt_bool_t = self._create_global_string("true\n", "fmt_true")
        self.fmt_bool_f = self._create_global_string("false\n", "fmt_false")
        self.fmt_str    = self._create_global_string("%s\n", "fmt_str")

    def _create_global_string(self, txt, name):
        try:
            b = bytearray(txt.encode("utf8") + b'\0')
        except:
            b = bytearray(txt + b'\0')
            
        ty = ir.ArrayType(char_type, len(b))
        g = ir.GlobalVariable(self.module, ty, name)
        g.linkage = 'internal'
        g.global_constant = True
        g.initializer = ir.Constant(ty, b)
        return g

    def _get_llvm_type(self, bminor_type_str):
        if bminor_type_str == 'integer': return int_type
        if bminor_type_str == 'float':   return float_type
        if bminor_type_str == 'boolean': return bool_type
        if bminor_type_str == 'char':    return char_type
        if bminor_type_str == 'string':  return string_type
        if bminor_type_str == 'void':    return void_type
        return int_type

    # =====================================================================
    # Manejo de Scope
    # =====================================================================
    def push_scope(self):
        self.scopes.append({})

    def pop_scope(self):
        self.scopes.pop()

    def add_symbol(self, name, value):
        self.scopes[-1][name] = value

    def get_symbol(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise Exception(f"Símbolo '{name}' no encontrado en generación de código.")

    # =====================================================================
    # HELPER: Obtener Dirección de Memoria (L-Value)
    # Fundamental para Assign, PreInc, PreDec y ArrayAccess
    # =====================================================================
    def _get_address(self, node):
        """
        Devuelve el PUNTERO (ir.Value) donde se debe almacenar/leer un valor.
        Maneja Identificadores y Accesos a Array.
        """
        if isinstance(node, Identifier):
            # Caso simple: variable x
            return self.get_symbol(node.name)
        
        elif isinstance(node, ArrayAccess):
            # Caso complejo: array[i]
            # 1. Obtener el puntero base del array
            base_ptr = self._get_address(node.array) # Recursivo por si es multi-dim
            
            # 2. Calcular el índice
            index_val = node.pos.accept(self)
            
            # 3. Generar GEP (Get Element Pointer)
            # En LLVM, para un puntero a array (alloca), necesitamos dos índices:
            # 0 (desreferenciar el puntero al array) y el index (posición deseada)
            zero = ir.Constant(int_type, 0)
            return self.builder.gep(base_ptr, [zero, index_val], inbounds=True)
            
        else:
            raise Exception(f"No se puede obtener la dirección de memoria de un nodo tipo {type(node)}")

    # =====================================================================
    # DISPATCHER
    # =====================================================================
    def visit(self, node):
        method_name = 'visit_' + type(node).__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        if isinstance(node, (Integer, Float, Boolean, String, Char)):
            return self.visit_Literal(node)
        if isinstance(node, VarDeclInit):
            return self.visit_VarDecl(node)
        # Fallback para listas de sentencias si el parser devuelve listas
        if isinstance(node, list):
            for item in node:
                self.visit(item)
            return
            
        raise Exception(f"No se encontró método visit_{type(node).__name__}")

    # =====================================================================
    # Estructura del Programa
    # =====================================================================

    def visit_Program(self, n: Program):
        for stmt in n.body:
            stmt.accept(self)
        return self.module

    def visit_FuncDecl(self, n: FuncDecl):
        ret_type = self._get_llvm_type(n.type_func.ret_type.name)
        param_types = [self._get_llvm_type(p.type.name) for p in n.params]
        func_type = ir.FunctionType(ret_type, param_types)
        
        if n.name in self.scopes[0]:
            func = self.scopes[0][n.name]
        else:
            func = ir.Function(self.module, func_type, name=n.name)
            self.add_symbol(n.name, func)

        self.function = func
        entry_block = func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(entry_block)

        self.push_scope() 

        for i, arg in enumerate(func.args):
            arg.name = n.params[i].name
            alloca = self.builder.alloca(param_types[i], name=arg.name)
            self.builder.store(arg, alloca)
            self.add_symbol(n.params[i].name, alloca)

        for stmt in n.body:
            stmt.accept(self)

        # === CORRECCIÓN ERROR WHILE/CHAR ===
        # Aseguramos el retorno para CUALQUIER tipo si el bloque no ha terminado
        if not self.builder.block.is_terminated:
            if ret_type == void_type:
                self.builder.ret_void()
            elif ret_type == float_type:
                self.builder.ret(ir.Constant(float_type, 0.0))
            else:
                # Int, Char, Bool -> Retornar entero 0 del tamaño correcto
                self.builder.ret(ir.Constant(ret_type, 0))

        self.pop_scope()
        self.function = None
        return func

  
    def visit_VarDecl(self, n: VarDecl):
        # --- ARRAY ---
        if isinstance(n.type, ArrayType):
            elem_type = self._get_llvm_type(n.type.elem_type.name)
            # Tamaño del array
            size = 10
            if hasattr(n.type.size, 'value'):
                 size = int(n.type.size.value)
            
            array_type = ir.ArrayType(elem_type, size)
            
            if len(self.scopes) == 1: # Global
                gvar = ir.GlobalVariable(self.module, array_type, n.name)
                # Las globales requieren inicializadores constantes complejos
                # Aquí usamos ZeroInitializer por simplicidad si no es trivial
                gvar.initializer = ir.Constant(array_type, [ir.Constant(elem_type, 0)] * size)
                self.add_symbol(n.name, gvar)
            else: # Local
                ptr = self.builder.alloca(array_type, name=n.name)
                self.add_symbol(n.name, ptr)
                
                # === CORRECCIÓN ERROR DE ARRAYS ===
                # Si hay valores iniciales {1, 2, ...}, hay que guardarlos uno a uno
                if n.value and isinstance(n.value, list):
                    zero = ir.Constant(int_type, 0)
                    for i, expr in enumerate(n.value):
                        # 1. Calcular valor
                        val = expr.accept(self)
                        # Cast si es necesario
                        if elem_type == int_type and val.type == bool_type:
                            val = self.builder.zext(val, int_type)
                        
                        # 2. Calcular índice constante
                        index = ir.Constant(int_type, i)
                        
                        # 3. Obtener puntero al elemento i: GEP(ptr, 0, i)
                        elem_ptr = self.builder.gep(ptr, [zero, index], inbounds=True)
                        
                        # 4. Guardar
                        self.builder.store(val, elem_ptr)

        # --- VARIABLE SIMPLE ---
        else:
            var_type = self._get_llvm_type(n.type.name)
            init_val = ir.Constant(var_type, 0)
            if var_type == float_type: init_val = ir.Constant(float_type, 0.0)

            if len(self.scopes) == 1: 
                gvar = ir.GlobalVariable(self.module, var_type, n.name)
                gvar.initializer = init_val 
                self.add_symbol(n.name, gvar)
            else:
                ptr = self.builder.alloca(var_type, name=n.name)
                if n.value:
                    val = n.value.accept(self)
                    if val.type == bool_type and var_type == int_type:
                        val = self.builder.zext(val, int_type)
                    self.builder.store(val, ptr)
                else:
                    self.builder.store(init_val, ptr)
                self.add_symbol(n.name, ptr)


    def visit_Block(self, n: Block):
        for stmt in n.body:
            stmt.accept(self)

    def visit_ReturnStmt(self, n: ReturnStmt):
        if n.expr:
            val = n.expr.accept(self)
            self.builder.ret(val)
        else:
            self.builder.ret_void()

    def visit_ExprStmt(self, n: ExprStmt):
        n.expr.accept(self)

    def visit_PrintStmt(self, n: PrintStmt):
        val = n.expr.accept(self)
        zero = ir.Constant(int_type, 0)
        
        if val.type == int_type:
            fmt, args = self.fmt_int, [val]
        elif val.type == float_type:
            fmt, args = self.fmt_float, [val]
        elif val.type == bool_type:
            str_true_ptr = self.builder.gep(self.fmt_bool_t, [zero, zero], inbounds=True)
            str_false_ptr = self.builder.gep(self.fmt_bool_f, [zero, zero], inbounds=True)
            fmt_str_ptr = self.builder.select(val, str_true_ptr, str_false_ptr)
            self.builder.call(self.printf, [fmt_str_ptr])
            return
        elif val.type == string_type or isinstance(val.type, ir.PointerType):
            fmt, args = self.fmt_str, [val]
        else:
            fmt, args = self.fmt_int, [val]

        fmt_ptr = self.builder.gep(fmt, [zero, zero], inbounds=True)
        self.builder.call(self.printf, [fmt_ptr] + args)

    def visit_IfStmt(self, n: IfStmt):
        cond_val = n.cond.accept(self)
        if cond_val.type != bool_type:
            cond_val = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0))

        then_block = self.function.append_basic_block(name="then")
        else_block = self.function.append_basic_block(name="else") if n.else_branch else None
        merge_block = self.function.append_basic_block(name="merge")

        target_else = else_block if else_block else merge_block
        self.builder.cbranch(cond_val, then_block, target_else)

        self.builder.position_at_end(then_block)
        for stmt in n.then_branch:
            stmt.accept(self)
        if not self.builder.block.is_terminated:
            self.builder.branch(merge_block)

        if else_block:
            self.builder.position_at_end(else_block)
            for stmt in n.else_branch:
                stmt.accept(self)
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_block)

        self.builder.position_at_end(merge_block)

    def visit_WhileStmt(self, n: WhileStmt):
        cond_block = self.function.append_basic_block(name="while_cond")
        body_block = self.function.append_basic_block(name="while_body")
        end_block  = self.function.append_basic_block(name="while_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        cond_val = n.cond.accept(self)
        if cond_val.type != bool_type:
            cond_val = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0))
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(body_block)
        for stmt in n.body:
            stmt.accept(self)
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)
        
        self.builder.position_at_end(end_block)

    # === NUEVO: DoWhileStmt ===
    def visit_DoWhileStmt(self, n: DoWhileStmt):
        body_block = self.function.append_basic_block(name="dowhile_body")
        cond_block = self.function.append_basic_block(name="dowhile_cond")
        end_block  = self.function.append_basic_block(name="dowhile_end")

        # Entrada incondicional al cuerpo
        self.builder.branch(body_block)

        # Cuerpo
        self.builder.position_at_end(body_block)
        n.body.accept(self) # DoWhile body suele ser un Block o Stmt
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        # Condición
        self.builder.position_at_end(cond_block)
        cond_val = n.cond.accept(self)
        if cond_val.type != bool_type:
            cond_val = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0))
        
        # Si True -> Vuelve al body, Si False -> Sale
        self.builder.cbranch(cond_val, body_block, end_block)

        self.builder.position_at_end(end_block)

    def visit_ForStmt(self, n: ForStmt):
        if n.init:
            n.init.accept(self)

        cond_block = self.function.append_basic_block(name="for_cond")
        body_block = self.function.append_basic_block(name="for_body")
        end_block  = self.function.append_basic_block(name="for_end")

        self.builder.branch(cond_block)

        self.builder.position_at_end(cond_block)
        if n.cond:
            cond_val = n.cond.accept(self)
            if cond_val.type != bool_type:
                 cond_val = self.builder.icmp_unsigned('!=', cond_val, ir.Constant(cond_val.type, 0))
            self.builder.cbranch(cond_val, body_block, end_block)
        else:
            self.builder.branch(body_block) 

        self.builder.position_at_end(body_block)
        
        # Corrección respecto a parser/model: ForStmt body a veces es block o list
        if isinstance(n.body, Block):
            n.body.accept(self)
        elif isinstance(n.body, list):
            for stmt in n.body:
                stmt.accept(self)
        else:
            n.body.accept(self)
        
        if n.step:
            n.step.accept(self)
        
        if not self.builder.block.is_terminated:
            self.builder.branch(cond_block)

        self.builder.position_at_end(end_block)

    # =====================================================================
    # Expresiones y Asignaciones
    # =====================================================================

    def visit_Assign(self, n: Assign):
        # Usamos el helper _get_address para soportar Arrays y Variables por igual
        ptr = self._get_address(n.left)
        val = n.right.accept(self)
        
        # Auto-cast simple (bool -> int) si es necesario
        if ptr.type.pointee == int_type and val.type == bool_type:
            val = self.builder.zext(val, int_type)
            
        self.builder.store(val, ptr)
        return val # Asignaciones pueden ser expr

    # === NUEVO: ArrayAccess (Lectura) ===
    def visit_ArrayAccess(self, n: ArrayAccess):
        # Obtener dirección del elemento
        ptr = self._get_address(n)
        # Cargar el valor
        return self.builder.load(ptr, name="array_val")

    # === NUEVO: PreInc (++x) ===
    def visit_PreInc(self, n: PreInc):
        # 1. Obtener dirección (l-value)
        ptr = self._get_address(n.expr)
        
        # 2. Cargar valor actual
        old_val = self.builder.load(ptr, name="preinc_load")
        
        # 3. Sumar 1 (Manejo de int vs float)
        one = ir.Constant(old_val.type, 1)
        if isinstance(old_val.type, ir.DoubleType):
            new_val = self.builder.fadd(old_val, one, name="inc_res")
        else:
            new_val = self.builder.add(old_val, one, name="inc_res")
            
        # 4. Guardar valor nuevo
        self.builder.store(new_val, ptr)
        
        # 5. Retornar nuevo valor
        return new_val

    # === NUEVO: PreDec (--x) ===
    def visit_PreDec(self, n: PreDec):
        ptr = self._get_address(n.expr)
        old_val = self.builder.load(ptr, name="predec_load")
        
        one = ir.Constant(old_val.type, 1)
        if isinstance(old_val.type, ir.DoubleType):
            new_val = self.builder.fsub(old_val, one, name="dec_res")
        else:
            new_val = self.builder.sub(old_val, one, name="dec_res")
            
        self.builder.store(new_val, ptr)
        return new_val

    # =====================================================================
    # Operadores
    # =====================================================================

    # === NUEVO: LogicalOpExpr (&&, || con Short-circuit) ===
    def visit_LogicalOpExpr(self, n: LogicalOpExpr):
        # Para && y ||, necesitamos bloques para evaluación perezosa (short-circuit)
        
        start_block = self.builder.block
        rhs_block = self.function.append_basic_block(name="logic_rhs")
        merge_block = self.function.append_basic_block(name="logic_merge")

        # 1. Evaluar LHS
        lhs_val = n.left.accept(self)
        if lhs_val.type != bool_type: # Asegurar boolean
             lhs_val = self.builder.icmp_unsigned('!=', lhs_val, ir.Constant(lhs_val.type, 0))
        
        # Recordar bloque LHS (puede cambiar si n.left generó nuevos bloques)
        lhs_end_block = self.builder.block 

        if n.oper == '&&':
            # Si LHS es True, evaluar RHS. Si False, saltar al final (result False).
            self.builder.cbranch(lhs_val, rhs_block, merge_block)
        elif n.oper == '||':
            # Si LHS es True, saltar al final (result True). Si False, evaluar RHS.
            self.builder.cbranch(lhs_val, merge_block, rhs_block)
        
        # 2. Bloque RHS
        self.builder.position_at_end(rhs_block)
        rhs_val = n.right.accept(self)
        if rhs_val.type != bool_type:
             rhs_val = self.builder.icmp_unsigned('!=', rhs_val, ir.Constant(rhs_val.type, 0))
        
        rhs_end_block = self.builder.block
        self.builder.branch(merge_block)

        # 3. Merge (Phi Node)
        self.builder.position_at_end(merge_block)
        phi = self.builder.phi(bool_type, name="logic_res")
        
        # Valores entrantes al Phi
        if n.oper == '&&':
            # Viene de LHS (False) o viene de RHS (resultado de RHS)
            phi.add_incoming(ir.Constant(bool_type, 0), lhs_end_block)
            phi.add_incoming(rhs_val, rhs_end_block)
        elif n.oper == '||':
             # Viene de LHS (True) o viene de RHS (resultado de RHS)
            phi.add_incoming(ir.Constant(bool_type, 1), lhs_end_block)
            phi.add_incoming(rhs_val, rhs_end_block)
            
        return phi

    def visit_BinOper(self, n: BinOper):
        lhs = n.left.accept(self)
        rhs = n.right.accept(self)

        if lhs.type == float_type and rhs.type == int_type:
            rhs = self.builder.sitofp(rhs, float_type)
        if rhs.type == float_type and lhs.type == int_type:
            lhs = self.builder.sitofp(lhs, float_type)

        is_float = lhs.type == float_type

        if n.oper == '+':
            return self.builder.fadd(lhs, rhs) if is_float else self.builder.add(lhs, rhs)
        elif n.oper == '-':
            return self.builder.fsub(lhs, rhs) if is_float else self.builder.sub(lhs, rhs)
        elif n.oper == '*':
            return self.builder.fmul(lhs, rhs) if is_float else self.builder.mul(lhs, rhs)
        elif n.oper == '/':
            return self.builder.fdiv(lhs, rhs) if is_float else self.builder.sdiv(lhs, rhs)
        elif n.oper == '%':
            return self.builder.frem(lhs, rhs) if is_float else self.builder.srem(lhs, rhs)
        
        # Comparaciones
        elif n.oper in ['<', '<=', '>', '>=', '==', '!=']:
            if is_float:
                return self.builder.fcmp_ordered(n.oper, lhs, rhs)
            else:
                return self.builder.icmp_signed(n.oper, lhs, rhs)

        return ir.Constant(int_type, 0)

    def visit_UnaryOper(self, n: UnaryOper):
        val = n.expr.accept(self)
        if n.oper == '-':
            if val.type == float_type:
                return self.builder.fneg(val)
            else:
                return self.builder.neg(val)
        elif n.oper == '!':
            return self.builder.not_(val)
        return val

    def visit_Literal(self, n: Literal):
        if n.type == 'integer': return ir.Constant(int_type, int(n.value))
        elif n.type == 'float': return ir.Constant(float_type, float(n.value))
        elif n.type == 'boolean': return ir.Constant(bool_type, 1 if n.value else 0)
        elif n.type == 'char': return ir.Constant(char_type, ord(n.value[0]) if n.value else 0)
        elif n.type == 'string':
            self.str_counter += 1
            gvar = self._create_global_string(n.value, f".str.{self.str_counter}")
            zero = ir.Constant(int_type, 0)
            return self.builder.gep(gvar, [zero, zero], inbounds=True)
        return ir.Constant(int_type, 0)

    def visit_Identifier(self, n: Identifier):
        # Carga simple de variable
        ptr = self.get_symbol(n.name)
        return self.builder.load(ptr, name=n.name)

    def visit_Call(self, n: Call):
        func = self.get_symbol(n.func.name)
        args = [arg.accept(self) for arg in n.args]
        return self.builder.call(func, args, name="calltmp")

# =====================================================================
# Main
# =====================================================================

if __name__ == '__main__':
    import sys
    from parser import parse

    if len(sys.argv) != 2:
        print("Uso: python llvm.py <archivo.bminor>")
        sys.exit(1)

    with open(sys.argv[1], encoding='utf-8') as f:
        code = f.read()

    ast = parse(code)
    
    generator = LLVMGenerator()
    try:
        llvm_ir = str(generator.visit(ast))
        print(llvm_ir)
    except Exception as e:
        print(f"; Error generando LLVM IR: {e}")
        import traceback
        traceback.print_exc()