# lexer.py
import sly

class Lexer(sly.Lexer):
    # -------------------
    # Tokens
    # -------------------
    tokens = {
        # Palabras reservadas
        ARRAY, AUTO, BOOLEAN, CHAR, ELSE, FALSE, FLOAT, FOR, FUNCTION,
        IF, INTEGER, PRINT, RETURN, STRING, TRUE, VOID, WHILE,
        # Literales
         FLOAT_LIT, CHAR_LIT, STRING_LIT, INT_LIT,
        # Operadores multi-char
        LE, GE, EQ, NEQ, AND, OR, INC, DEC, NOT,
        # Otros
        ID, LOR, LAND, LT, LE, GT, GE, EQ, NEQ, INC, DEC, NOT
    }

    # Literales de un solo carácter
    literals = '+-*/%^=()[]{}:;,<>!'

    # Ignorar espacios y tabs
    ignore = ' \t\r'

    # -------------------
    # Manejo de líneas
    # -------------------
    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += len(t.value)

    # -------------------
    # Comentarios
    # -------------------
    @_(r'//.*')
    def ignore_cpp_comment(self, t):
        pass

    @_(r'/\*(.|\n)*?\*/')
    def ignore_c_comment(self, t):
        self.lineno += t.value.count('\n')

    # -------------------
    # Identificadores y palabras clave
    # -------------------



    ID = r"[a-zA-Z_][a-zA-Z0-9_]*"
    ID['array']    = ARRAY
    ID['auto']     = AUTO
    ID['boolean']  = BOOLEAN
    ID['char']     = CHAR
    ID['else']     = ELSE
    ID['false']    = FALSE
    ID['float']    = FLOAT
    ID['for']      = FOR
    ID['function'] = FUNCTION
    ID['if']       = IF
    ID['integer']  = INTEGER
    ID['print']    = PRINT
    ID['return']   = RETURN
    ID['string']   = STRING
    ID['true']     = TRUE
    ID['void']     = VOID
    ID['while']    = WHILE

    ID['LOR']      = LOR
    ID['LAND']     = LAND
    ID['LT']       = LT
    ID['LE']       = LE
    ID['GT']       = GT
    ID['GE']       = GE
    ID['EQ']       = EQ
    ID['NEQ']      = NEQ
    ID['INC']      = INC
    ID['DEC']      = DEC
    ID['NOT']      = NOT

    # # Validar longitud de identificadores (<= 255)
    # def ID(self, t):
    #     if len(t.value) > 255:
    #         self.error(t)
    #         return None
    #     return t

    # -------------------
    # Operadores multi-char
    # -------------------
    LE  = r'<='
    GE  = r'>='
    EQ  = r'=='
    NEQ = r'!='
    AND = r'&&'
    OR  = r'\|\|'
    INC = r'\+\+'
    DEC = r'--'
    NOT = r'!'

    @_(r'(0|[1-9][0-9]*)')
    def INT_LIT(self, t):
        t.value = int(t.value)
        return t


    # Flotantes: .123 | 123. | 123.45 | 1e10 | 1.2E-3
    @_(r'((0(?!\d))|([1-9]\d*))((\.\d+(e[-+]?\d+)?)|([eE][-+]?\d+))')
    def FLOAT_LIT(self, t):
        t.value = float(t.value)
        return t

 
    @_(r'0\d+')
    def malformed_inumber(self, t):
        self.error(t)

    # -------------------
    # Literales char y string
    # -------------------
    # Caracter: 'a' o con escapes válidos
    @_(r"'(\\[abefnrtv\\\'\"0x][0-9a-fA-F]*|[^\\'])'")
    def CHAR_LIT(self, t):
        s = t.value[1:-1]
        try:
            t.value = bytes(s, "utf-8").decode("unicode_escape")
        except Exception:
            self.error(t)
            return None
        return t

    # Cadena: "..." con escapes válidos
    @_(r'"(\\[abefnrtv\\\'\"0x][0-9a-fA-F]*|[^\\"])*"')
    def STRING_LIT(self, t):
        s = t.value[1:-1]
        if len(s) > 255:
            self.error(t)
            return None
        try:
            t.value = bytes(s, "utf-8").decode("unicode_escape")
        except Exception:
            self.error(t)
            return None
        return t

    # -------------------
    # Manejo de errores
    # -------------------
    def error(self, t):
        print(f"Line {self.lineno}: Bad character {t.value[0]!r}")
        self.index += 1
        sys.exit(1)


def tokenize(txt):
    lexer = Lexer()

    for tok in lexer.tokenize(txt):
        print(tok)

if __name__ == '__main__':
    import sys

    if len(sys.argv) != 2:
        print("usage: python lexer.py filename")
        exit(1)
    
    tokenize(open(sys.argv[1], encoding='utf-8').read())