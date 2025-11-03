# grammar.py
import logging
import sly
from rich import print
from rich.tree import Tree
from lexer  import Lexer
from errors import error, errors_detected
from model  import *	# AST Definitions

def _L(node, lineno):
	node.lineno = lineno
	return node

def print_ast(node, label="AST"):
    tree = Tree(label)
    _build_tree(node, tree)
    print(tree)

def _build_tree(node, tree):
    if isinstance(node, list):
        for i, child in enumerate(node):
            branch = tree.add(f"[list] {i}")
            _build_tree(child, branch)

    elif hasattr(node, "__dict__"):
        branch = tree.add(node.__class__.__name__)
        for key, value in vars(node).items():
            child_branch = branch.add(f"{key}")
            _build_tree(value, child_branch)
    else:
        tree.add(str(node))

class Parser(sly.Parser):
	log = logging.getLogger()
	log.setLevel(logging.ERROR)
	expected_shift_reduce = 1
	debugfile='grammar.txt'

	tokens = Lexer.tokens

	@_("decl_list")
	def prog(self, p):
		return _L(Program(p.decl_list), getattr(p.decl_list, "lineno", 0))
	
	# Declarations

	@_("decl_list decl")
	def decl_list(self, p):
		return p.decl_list + [p.decl]

	@_("decl")
	def decl_list(self, p):
		return [p.decl]

	@_("ID ':' type_simple ';'")
	def decl(self, p):
		return VarDecl(p.ID, p.type_simple)

	@_("ID ':' type_array_sized ';'")
	def decl(self, p):
		return VarDecl(p.ID, p.type_array_sized)

	@_("ID ':' type_func ';'")
	def decl(self, p):
		return FuncDecl(p.ID, p.type_func)

	@_("decl_init")
	def decl(self, p):
		return p.decl_init

	# -------------------------
	# Declarations with init
	# -------------------------

	@_("ID ':' type_simple '=' expr ';'")
	def decl_init(self, p):
		return VarDeclInit(p.ID, p.type_simple, p.expr)

	@_("ID ':' type_array_sized '=' '{' opt_expr_list '}' ';'")
	def decl_init(self, p):
		return VarDeclInit(p.ID, p.type_array_sized, p.opt_expr_list)

	@_("ID ':' type_func '=' '{' opt_stmt_list '}'")
	def decl_init(self, p):
		return FuncDecl(p.ID, p.type_func, p.opt_stmt_list)


	# Statements

	# =====================
	# Statements
	# =====================

	@_("stmt_list")
	def opt_stmt_list(self, p):
		return p.stmt_list

	@_("empty")
	def opt_stmt_list(self, p):
		return []

	@_("stmt_list stmt")
	def stmt_list(self, p):
		return p.stmt_list + [p.stmt]

	@_("stmt")
	def stmt_list(self, p):
		return [p.stmt]

	@_("closed_stmt")
	def stmt(self, p):
		return p[0]

	@_("simple_stmt")
	def closed_stmt(self, p):
		return p[0]


	# ---------------------
	# Simple statements (no recursivos)
	# ---------------------

	@_("return_stmt")
	@_("block_stmt")
	@_("decl")
	@_("if_stmt")
	@_("for_stmt")
	@_("while_stmt")
	@_("do_while_stmt")
	@_("expr ';'")
	def simple_stmt(self, p):
		return p[0]

	@_("RETURN opt_expr ';'")
	def return_stmt(self, p):
		return ReturnStmt(p.opt_expr)

	@_("'{' stmt_list '}'")
	def block_stmt(self, p):
		return Block(p.stmt_list)

	# if
	@_("IF '(' opt_expr ')'")
	def if_header(self, p):
		return p.opt_expr

	# Regla para `if-else`. La parte `else` puede ser otra sentencia `if`
    # (manejando `else if`) o un bloque (manejando el `else` final).
    # SLY resuelve la ambigüedad del "dangling else" prefiriendo esta regla
    # sobre la de `if` sin `else` (acción de "shift").
	@_("if_header '{' opt_stmt_list '}' ELSE '{' opt_stmt_list '}'")
	def if_stmt(self, p):
		opt_expr = p.if_header
		return IfStmt(opt_expr, p.opt_stmt_list0, p.opt_stmt_list1)

	@_("if_header '{' opt_stmt_list '}'")
	def if_stmt(self, p):
		opt_expr = p.if_header
		return IfStmt(IfCond(opt_expr), p.opt_stmt_list)

	# for
	@_("FOR '(' opt_expr ';' opt_expr ';' opt_expr ')'")
	def for_header(self, p):
		return (p.opt_expr0, p.opt_expr1, p.opt_expr2)

	@_("for_header '{' stmt_list '}'")
	def for_stmt(self, p):
		init, cond, step = p.for_header
		return ForStmt(init, cond, step, p.stmt_list)

	# while
	@_("WHILE '(' opt_expr ')'")
	def while_header(self, p):
		return p.opt_expr

	@_("while_header '{' stmt_list '}'")
	def while_stmt(self, p):
		return WhileStmt(p.while_header, p.stmt_list)

	@_('DO stmt while_header ";"')
	def do_while_stmt(self, p):
		return DoWhileStmt(p.stmt, p.while_header)

	
	
	# =====================
	# Expressions
	# =====================

	@_("empty")
	def opt_expr_list(self, p):
		return []

	@_("expr_list")
	def opt_expr_list(self, p):
		return p.expr_list

	@_("expr ',' expr_list")
	def expr_list(self, p):
		return [p.expr] + p.expr_list

	@_("expr")
	def expr_list(self, p):
		return [p.expr]

	# ---------------------
	# Optional single expr
	# ---------------------

	@_("empty")
	def opt_expr(self, p):
		return None

	@_("expr")
	def opt_expr(self, p):
		return p.expr

	# ---------------------
	# Assignment
	# ---------------------

	@_("expr1")
	def expr(self, p):
		return p.expr1

	@_("lval '=' expr1")
	def expr1(self, p):
		return Assign(p.lval, p.expr1)

	@_("expr2")
	def expr1(self, p):
		return p.expr2

	@_("ID")
	def lval(self, p):
		return Identifier(p.ID)

	@_("ID indexPos")
	def lval(self, p):
		return ArrayAccess(Identifier(p.ID), p.indexPos)

	# ---------------------
	# Logical OR
	# ---------------------

	@_("expr2 LOR expr3")
	def expr2(self, p):
		return LogicalOpExpr("||", p.expr2, p.expr3)

	@_("expr3")
	def expr2(self, p):
		return p.expr3

	# ---------------------
	# Logical AND
	# ---------------------

	@_("expr3 AND expr4")
	def expr3(self, p):
		return LogicalOpExpr("&&", p.expr3, p.expr4)

	@_("expr4")
	def expr3(self, p):
		return p.expr4

	# ---------------------
	# Relational & Equality
	# ---------------------

	@_("expr4 EQ expr5")
	@_("expr4 NEQ expr5")
	@_("expr4 LT expr5")
	@_("expr4 LE expr5")
	@_("expr4 GT expr5")
	@_("expr4 GE expr5")
	def expr4(self, p):
		return BinOper(p[1], p.expr4, p.expr5)

	@_("expr5")
	def expr4(self, p):
		return p.expr5

	# ---------------------
	# Addition / Subtraction
	# ---------------------

	@_("expr5 '+' expr6")
	@_("expr5 '-' expr6")
	def expr5(self, p):
		return BinOper(p[1], p.expr5, p.expr6)

	@_("expr6")
	def expr5(self, p):
		return p.expr6

	# ---------------------
	# Multiplication / Division / Mod
	# ---------------------

	@_("expr6 '*' expr7")
	@_("expr6 '/' expr7")
	@_("expr6 '%' expr7")
	def expr6(self, p):
		return BinOper(p[1], p.expr6, p.expr7)

	@_("expr7")
	def expr6(self, p):
		return p.expr7

	# ---------------------
	# Power ^
	# ---------------------

	@_("expr7 '^' expr8")
	def expr7(self, p):
		return BinOper("^", p.expr7, p.expr8)

	@_("expr8")
	def expr7(self, p):
		return p.expr8

	# ---------------------
	# Unary - and !
	# ---------------------

	@_("'-' expr8")
	@_("'!' expr8")
	def expr8(self, p):
		return UnaryOper(p[0], p.expr8)

	@_("expr9")
	def expr8(self, p):
		return p.expr9

	# ---------------------
	# Postfix ++ / --
	# ---------------------

	@_("expr9 INC")
	def expr9(self, p):
		return BinOper("post++", p.expr9, None)

	@_("expr9 DEC")
	def expr9(self, p):
		return BinOper("post--", p.expr9, None)

	# ---------------------
	# Groups and higher constructs
	# ---------------------

	@_("group")
	def expr9(self, p):
		return p.group

	@_("'(' expr ')'")
	def group(self, p):
		return p.expr

	@_("ID '(' opt_expr_list ')'")
	def group(self, p):
		return Call(Identifier(p.ID), p.opt_expr_list)

	@_("PRINT expr")
	def group(self, p):
		return PrintStmt(p.expr)

	@_("ID indexPos")
	def group(self, p):
		return ArrayAccess(Identifier(p.ID), p.indexPos)

	@_("factor")
	def group(self, p):
		return p.factor

	# ---------------------
	# Array index
	# ---------------------

	@_("'[' expr ']'")
	def indexPos(self, p):
		return p.expr

	# ---------------------
	# Factors (literals, identifiers)
	# ---------------------

	@_("ID")
	def factor(self, p):
		return Identifier(p.ID)

	@_("INT_LIT")
	def factor(self, p):
		return _L(Integer(p.INT_LIT), p.lineno)

	@_("FLOAT_LIT")
	def factor(self, p):
		return _L(Float(p.FLOAT_LIT), p.lineno)

	@_("CHAR_LIT")
	def factor(self, p):
		return _L(Char(p.CHAR_LIT), p.lineno)

	@_("STRING_LIT")
	def factor(self, p):
		return _L(String(p.STRING_LIT), p.lineno)

	@_("TRUE")
	def factor(self, p):
		return _L(Boolean(True), p.lineno)

	@_("FALSE")
	def factor(self, p):
		return _L(Boolean(False), p.lineno)

		

	# -----------------
	# Types
	# -----------------

	@_("INTEGER")
	@_("FLOAT")
	@_("BOOLEAN")
	@_("CHAR")
	@_("STRING")
	@_("VOID")
	def type_simple(self, p):
		return SimpleType(p[0])

	@_("ARRAY '[' ']' type_simple")
	@_("ARRAY '[' ']' type_array")
	def type_array(self, p):
		# tamaño vacío => None
		return ArrayType(None, p[-1])

	@_("ARRAY indexPos type_simple")
	@_("ARRAY indexPos type_array_sized")
	def type_array_sized(self, p):
		return ArrayType(p.indexPos, p[-1])

	@_("FUNCTION type_simple '(' opt_param_list ')'")
	@_("FUNCTION type_array_sized '(' opt_param_list ')'")
	def type_func(self, p):
		return FuncType(p[1], p.opt_param_list)

	@_("empty")
	def opt_param_list(self, p):
		return []

	@_("param_list")
	def opt_param_list(self, p):
		return p.param_list

	@_("param_list ',' param")
	def param_list(self, p):
		return p.param_list + [p.param]

	@_("param")
	def param_list(self, p):
		return [p.param]

	@_("ID ':' type_simple")
	def param(self, p):
		return Param(p.ID, p.type_simple)

	@_("ID ':' type_array")
	def param(self, p):
		return Param(p.ID, p.type_array)

	@_("ID ':' type_array_sized")
	def param(self, p):
		return Param(p.ID, p.type_array_sized)

	@_("")
	def empty(self, p):
		return None
	
	
	
	@_("INC expr9")
	def expr9(self, p):
		return PreInc(p.expr9)

	@_("DEC expr9")
	def expr9(self, p):
		return PreDec(p.expr9)

	def error(self, p):
		if p:
			lineno = p.lineno if p else 'EOF'
			value = repr(p.value) if p else 'EOF'
			# expected = self.state.expect  # tokens esperados en ese estado
			# print(f"Syntax error at line {lineno}: unexpected {value} ({p.type}) ")
			raise SyntaxError(f"Syntax error at line {lineno}: unexpected {value} ({p.type})")
		else:
			print("Syntax error at EOF")
		# create exception



# Convertir el AST a una representación JSON para mejor visualización
def ast_to_dict(node):
	if isinstance(node, list):
		return [ast_to_dict(item) for item in node]
	elif hasattr(node, "__dict__"):
		return {key: ast_to_dict(value) for key, value in node.__dict__.items()}
	else:
		return node


def parse(txt):
	l = Lexer()
	p = Parser()
	return p.parse(l.tokenize(txt))

if __name__ == '__main__':
	import sys, json
	
	if sys.platform != 'ios':

		if len(sys.argv) != 2:
			raise SystemExit("Usage: python gparse.py <filename>")

		filename = sys.argv[1]

	else:
		from File_Picker import file_picker_dialog

		filename = file_picker_dialog(
			title='Seleccionar una archivo',
			root_dir='./test',
			file_pattern='^.*[.]bminor'
		)

	if filename:
		txt = open(filename, encoding='utf-8').read()
		ast = parse(txt)

		# detect errors
		if (ast):
			dicts = print_ast(ast)
			print(dicts)
			

		