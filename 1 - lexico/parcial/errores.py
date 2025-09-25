# Prueba de A1/A2 (opcional)
# Ejecuta el lexer sobre una cadena con un carácter ilegal '@'
import importlib, sys, types
from lexer  import LexerSLY

lx = LexerSLY()
data = "x := 3 + @"
for tok in lx.tokenize(data):
    print(tok)
