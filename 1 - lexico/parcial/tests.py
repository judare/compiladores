# Prueba de A1/A2 (opcional)
# Ejecuta el lexer sobre una cadena con un carácter ilegal '@'
import importlib, sys, types
from lexer  import LexerSLY

tests = [
    "x := 1 + 2",
    "while x do x := x + 1",
]

if __name__ == '__main__':
    lx = LexerSLY()

    # lexer tests
    for s in tests:
        for tok in lx.tokenize(s):
            print(tok)
