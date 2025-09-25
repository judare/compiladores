
from sly import Lexer
import sys

class LexerSLY(Lexer):
    tokens = { ID, INT, PLUS, ASSIGN, WHILE, DO, LPAREN, RPAREN }
    ignore = ' \t'

    # Palabras reservadas via re-map sobre ID
    ID = r'[A-Za-z_][A-Za-z0-9_]*'
    ID['while'] = 'WHILE'
    ID['do']    = 'DO'

    # Operadores y símbolos
    PLUS   = r'\+'
    ASSIGN = r':='
    LPAREN = r'\('
    RPAREN = r'\)'

    INT = r'\d+'

    # Comentarios de línea estilo //...
    ignore_comment = r'//.*'

    @_(r'\n+')
    def newline(self, t):
        self.lineno += t.value.count('\n')


    # -------------------
    # Manejo de errores
    # -------------------
    def error(self, t):
        print(f"Line {self.lineno}: Bad character {t.value[0]!r}")
        self.index += 1
        sys.exit(1)


        

if __name__ == "__main__":
    data = "while x do y := y + 1"
    lx = LexerSLY()
    for tok in lx.tokenize(data):
        print(tok)
