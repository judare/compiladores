# lexer.py
#
# Analizador Léxico para el lenguaje B-Minor

import sly

class Lexer(sly.Lexer):
    tokens = {
        # Palabras Reservadas
        ARRAY, AUTO, BOOLEAN, CHAR, ELSE, FALSE, FLOAT, FOR, FUNCTION,
        IF, INTEGER, PRINT, RETURN, STRING, TRUE, VOID, WHILE,

        # Otros simbolos
        ID,
    }
    literals = '+-*/%^=()[]{}:;,'

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
    ID['array'] = ARRAY
    ID['auto']  = AUTO
    ID['boolean'] = BOOLEAN
    ID['char']  = CHAR


    def error(self, t):
        print(f"Line {self.lineno}: Bad character '{t.value[0]}'")
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