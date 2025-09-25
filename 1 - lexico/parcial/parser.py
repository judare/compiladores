from sly import Parser
from lexer import LexerSLY

class ParserSLY(Parser):
    tokens = LexerSLY.tokens
    debugfile = 'parsing.out'   # SLY generará este archivo al construir el parser

    # E10. Ajuste la precedencia segun su análisis:
    # De menor a mayor: ASSIGN (derecha), luego PLUS (izquierda)
    precedence = (
        ('right', 'ASSIGN'),
        ('left',  'PLUS'),
    )

    # Símbolo inicial S
    @_('E')
    def S(self, p):
        return p.E

    @_('WHILE E DO E')
    def E(self, p):
        return ('while', p.E0, p.E1)

    @_('ID ASSIGN E')
    def E(self, p):
        return ('assign', p.ID, p.E)

    @_('E PLUS E')
    def E(self, p):
        return ('add', p.E0, p.E1)

    @_('ID')
    def E(self, p):
        return ('var', p.ID)



if __name__ == '__main__':
    lx = LexerSLY()
    ps = ParserSLY()

    import sys
    data = sys.stdin.read()
    result = ps.parse(lx.tokenize(data))
    print(result)
    
