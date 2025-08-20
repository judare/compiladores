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
        INT_LIT, FLOAT_LIT, CHAR_LIT, STRING_LIT,
        # Operadores multi-char
        LE, GE, EQ, NEQ, AND, OR, INC, DEC, NOT,
        # Otros
        ID
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
    ID = r'[_a-zA-Z]\w*'

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

    # Validar longitud de identificadores (<= 255)
    def ID(self, t):
        if len(t.value) > 255:
            self.error(t)
            return None
        return t

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

    # -------------------
    # Literales numéricos
    # -------------------
    @_(r'0[xX][0-9a-fA-F]+')
    def INT_LIT(self, t):
        t.value = int(t.value, 16)
        return t

    @_(r'0[0-7]+')
    def INT_LIT(self, t):
        t.value = int(t.value, 8)
        return t

    # Flotantes: .123 | 123. | 123.45 | 1e10 | 1.2E-3
    @_(r'[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?|[+-]?\d+[eE][+-]?\d+')
    def FLOAT_LIT(self, t):
        t.value = float(t.value)
        return t

    @_(r'\d+')
    def INT_LIT(self, t):
        t.value = int(t.value)
        return t

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