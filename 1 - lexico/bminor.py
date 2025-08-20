

## usage
# bminor.py --scan test/test.bminor

import sys
import os
import argparse
from subprocess import Popen, PIPE

def main():
    parser = argparse.ArgumentParser(description='bminor')
    parser.add_argument('--scan', help='scan a file')
    args = parser.parse_args()

    if args.scan:
        scan(args.scan)

def scan(file):
    cmd = ['./bminor', file]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    if stderr:
        print(stderr)
    else:
        print(stdout)

if __name__ == '__main__':
    main()


## pruebas para
# palabras reservadas
# identificadores
# literales: char, string, integer, float, boolean