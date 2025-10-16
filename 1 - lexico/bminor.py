

## usage
# bminor.py --scan test/test.bminor

import argparse
from subprocess import Popen, PIPE

def main():
    parser = argparse.ArgumentParser(description='bminor')
    parser.add_argument('--scan', help='scan a file')
    parser.add_argument('--parse', help='parse a file')
    parser.add_argument('--checker', help='checker a file')
    parser.add_argument('--ast', help='show ast')
    args = parser.parse_args()

    if args.scan:
        scan(args.scan)
    elif args.parse:
        parse(args.parse)
    elif args.checker:
        checker(args.checker)
    elif args.ast:
        ast(args.ast)

def scan(file):
    cmd = ["python3", './lexer.py', file]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    stdout, stderr = p.communicate()
    if stderr:
        print(stderr)
    else:
        print(stdout)

def parse(file):
    cmd = ["python3", './parser.py', file]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    stdout, stderr = p.communicate()
    if stderr:
        print(stderr)
    else:
        # print with lines 
        print(stdout)


def checker(file):
    cmd = ["python3", './checker.py', file]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    stdout, stderr = p.communicate()
    if stderr:
        print(stderr)
    else:
        # print with lines 
        print(stdout)
    

def ast(file):
    cmd = ["python3", './astprint.py', file]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE, encoding='utf-8')
    stdout, stderr = p.communicate()
    if stderr:
        print(stderr)
    else:
        # print with lines 
        print(stdout)
    

if __name__ == '__main__':
    main()


## pruebas para
# palabras reservadas
# identificadores
# literales: char, string, integer, float, boolean