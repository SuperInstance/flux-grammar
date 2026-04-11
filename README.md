# FLUX Grammar — Formal Assembly Language Specification

Lexer, parser, and validator for the FLUX assembly language.

## Architecture
- **Lexer**: Tokenizes source into OPCODE, REGISTER, IMMEDIATE, LABEL_DEF, COMMENT tokens
- **Parser**: Builds AST with InstructionNode, LabelNode, ProgramNode
- **Validator**: Checks operand counts and types against opcode signatures

## Language Reference

```
program     = { line }
line        = label | instruction | comment | blank
instruction = opcode { operand }
operand     = register | immediate
register    = "R" digit+
immediate   = ["-"] decimal | "0x" hex
comment     = ";" text
```

## Example

```python
from grammar import Lexer, Parser, Validator

source = """
    MOVI R0, 10      ; counter
    MOVI R1, 0       ; accumulator
loop:
    INC R1
    DEC R0
    JNZ R0, loop     ; back to INC
    HALT
"""

tokens = Lexer(source).tokens
program = Parser(tokens).parse()
validator = Validator(program)
assert validator.validate()
```

16 tests passing.
