#!/usr/bin/env python
import ast
import sys

try:
    with open('app.py', 'r', encoding='utf-8') as f:
        source = f.read()

    ast.parse(source)
    print("✅ Syntax is valid!")
    sys.exit(0)
except SyntaxError as e:
    print(f"❌ Syntax Error at line {e.lineno}: {e.msg}")
    print(f"   {e.text}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
