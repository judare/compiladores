# lexer.py
#
# Analizador Léxico para el lenguaje B-Minor

import sly

class Lexer(sly.Lexer):
    tokens = {
        # Palabras Reservadas
        ARRAY, AUTO, BOOLEAN, CHAR, ELSE, FALSE, FLOAT, FOR, FUNCTION,
        IF, INTEGER, PRINT, RETURN, TRUE, VOID, WHILE,
        INT_LIT, FLOAT_LIT, CHAR_LIT,
        # Otros simbolos
        ID
    }

    literals = '+-*/%^=()[]{}:;,<>'
    # literals = '+-*/%^=()[]{}:;,<>!'

    # Caracteres a ignoras
    ignore = ' \t\r'

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno = t.value.count('\n')
    
    @_(r'//.*')
    def ignore_cppcomment(self, t):
        pass
    
    @_(r'/\*(.|\n)*\*/')
    def ignore_comment(self, t):
        self.lineno = t.value.count('\n')
    
    # Identificador y Palabras reservadas
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
    ID['true']     = TRUE
    ID['void']     = VOID
    ID['while']    = WHILE


    @_(r'\d+\.\d*([eE][+-]?\d+)?|\d+[eE][+-]?\d+')
    def FLOAT_LIT(self, t):
        t.value = float(t.value)
        return t

    @_(r'\d+')
    def INT_LIT(self, t):
        t.value = int(t.value)
        return t


    @_(r'[0-9]+')
    def INT(self, t):
        t.value = int(t.value)
        return t


    # Manejo de errores
    def error(self, t):
        print(f"Line {self.lineno}: Bad character {t.value[0]!r}")
        self.index += 1

    # Literales numéricos
    @_(r'0[xX][0-9a-fA-F]+')
    def INT_LIT(self, t):
        t.value = int(t.value, 16)
        return t

    # @_(r"'(\\.|[^\\'])'")
    @_(r"'([\x20-\x7E]|\\([abefnrtv'\"\\]|0x[0-9A-Fa-f]{1,2}))'")
    def CHAR_LIT(self, t):
        s = t.value[1:-1]
        t.value = bytes(s, "utf-8").decode("unicode_escape")
        return t

    # Literal de cadena
    @_(r'"(\\.|[^\\"])*"')
    def CHAR_LIT(self, t):
        s = t.value[1:-1]
        t.value = bytes(s, "utf-8").decode("unicode_escape")
        return t

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