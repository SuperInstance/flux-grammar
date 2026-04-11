"""
FLUX Assembly Grammar — Formal specification and parser.

Defines the complete FLUX assembly language:
  program     = { line }
  line        = label | instruction | comment | blank
  label       = identifier ":"
  instruction = opcode { operand }
  operand     = register | immediate | label_ref
  register    = "R" digit | "r" digit
  immediate   = ["-"] decimal | "0x" hex
  comment     = ";" text
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import Enum, auto


class TokenType(Enum):
    OPCODE = auto()
    REGISTER = auto()
    IMMEDIATE = auto()
    LABEL_DEF = auto()
    LABEL_REF = auto()
    COMMENT = auto()
    NEWLINE = auto()
    COMMA = auto()
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    col: int


@dataclass
class ASTNode:
    """Base AST node."""
    type: str
    line: int


@dataclass
class InstructionNode(ASTNode):
    opcode: str
    operands: List[str] = field(default_factory=list)
    operand_types: List[str] = field(default_factory=list)


@dataclass 
class LabelNode(ASTNode):
    name: str


@dataclass
class ProgramNode(ASTNode):
    instructions: List[ASTNode] = field(default_factory=list)
    labels: dict = field(default_factory=dict)


OPCODES = {
    'HALT', 'NOP', 'INC', 'DEC', 'NOT', 'NEG', 'PUSH', 'POP',
    'STRIPCONF', 'MOVI', 'ADDI', 'SUBI',
    'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'XOR', 'SHL', 'SHR',
    'MIN', 'MAX', 'CMP_EQ', 'CMP_LT', 'CMP_GT', 'CMP_NE',
    'MOV', 'JZ', 'JNZ', 'MOVI16', 'JMP', 'LOOP',
}

# Format signatures: opcode -> list of operand types
SIGNATURES = {
    'HALT': [], 'NOP': [],
    'INC': ['reg'], 'DEC': ['reg'], 'NOT': ['reg'], 'NEG': ['reg'],
    'PUSH': ['reg'], 'POP': ['reg'], 'STRIPCONF': ['reg'],
    'MOVI': ['reg', 'imm'], 'ADDI': ['reg', 'imm'], 'SUBI': ['reg', 'imm'],
    'ADD': ['reg', 'reg', 'reg'], 'SUB': ['reg', 'reg', 'reg'],
    'MUL': ['reg', 'reg', 'reg'], 'DIV': ['reg', 'reg', 'reg'],
    'MOD': ['reg', 'reg', 'reg'],
    'AND': ['reg', 'reg', 'reg'], 'OR': ['reg', 'reg', 'reg'],
    'XOR': ['reg', 'reg', 'reg'],
    'SHL': ['reg', 'reg', 'reg'], 'SHR': ['reg', 'reg', 'reg'],
    'MIN': ['reg', 'reg', 'reg'], 'MAX': ['reg', 'reg', 'reg'],
    'CMP_EQ': ['reg', 'reg', 'reg'], 'CMP_LT': ['reg', 'reg', 'reg'],
    'CMP_GT': ['reg', 'reg', 'reg'], 'CMP_NE': ['reg', 'reg', 'reg'],
    'MOV': ['reg', 'reg', 'reg'],
    'JZ': ['reg', 'imm'], 'JNZ': ['reg', 'imm'],
    'MOVI16': ['reg', 'imm'],
    'JMP': ['imm'], 'LOOP': ['reg', 'imm'],
}


class Lexer:
    """Tokenize FLUX assembly source."""
    
    PATTERNS = [
        (TokenType.COMMENT, r';[^\n]*'),
        (TokenType.LABEL_DEF, r'[a-zA-Z_][a-zA-Z0-9_]*:'),
        (TokenType.OPCODE, r'(?:' + '|'.join(sorted(OPCODES, key=len, reverse=True)) + r')\b'),
        (TokenType.REGISTER, r'[Rr]\d+'),
        (TokenType.IMMEDIATE, r'-?(?:0[xX][0-9a-fA-F]+|\d+)'),
        (TokenType.LABEL_REF, r'[a-zA-Z_][a-zA-Z0-9_]*'),
        (TokenType.COMMA, r','),
        (TokenType.NEWLINE, r'\n'),
    ]
    
    def __init__(self, source: str):
        self.source = source
        self.tokens: List[Token] = []
        self.tokenize()
    
    def tokenize(self):
        pos = 0
        line = 1
        col = 1
        
        while pos < len(self.source):
            # Skip whitespace (not newlines)
            if self.source[pos] in ' \t\r':
                pos += 1
                col += 1
                continue
            
            matched = False
            for token_type, pattern in self.PATTERNS:
                regex = re.compile(pattern)
                m = regex.match(self.source, pos)
                if m:
                    value = m.group(0)
                    self.tokens.append(Token(token_type, value, line, col))
                    
                    if token_type == TokenType.NEWLINE:
                        line += 1
                        col = 1
                    else:
                        col += len(value)
                    
                    pos = m.end()
                    matched = True
                    break
            
            if not matched:
                self.tokens.append(Token(TokenType.EOF, self.source[pos], line, col))
                pos += 1
                col += 1
        
        self.tokens.append(Token(TokenType.EOF, '', line, col))


class Parser:
    """Parse tokenized FLUX assembly into AST."""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0
    
    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, '', 0, 0)
    
    def advance(self) -> Token:
        t = self.current()
        self.pos += 1
        return t
    
    def expect(self, token_type: TokenType) -> Token:
        t = self.current()
        if t.type != token_type:
            raise SyntaxError(f"Expected {token_type}, got {t.type} ('{t.value}') at line {t.line}")
        return self.advance()
    
    def parse(self) -> ProgramNode:
        program = ProgramNode(type="program", line=1)
        
        while self.current().type != TokenType.EOF:
            t = self.current()
            
            if t.type == TokenType.NEWLINE:
                self.advance()
                continue
            
            if t.type == TokenType.COMMENT:
                self.advance()
                continue
            
            if t.type == TokenType.LABEL_DEF:
                name = t.value[:-1]
                program.labels[name] = len(program.instructions)
                program.instructions.append(LabelNode(type="label", line=t.line, name=name))
                self.advance()
                continue
            
            if t.type == TokenType.OPCODE:
                instr = self.parse_instruction()
                program.instructions.append(instr)
                continue
            
            # Skip unknown tokens
            self.advance()
        
        return program
    
    def parse_instruction(self) -> InstructionNode:
        t = self.advance()
        opcode = t.value.upper()
        
        operands = []
        operand_types = []
        
        while self.current().type in (TokenType.REGISTER, TokenType.IMMEDIATE, 
                                       TokenType.LABEL_REF, TokenType.COMMA):
            if self.current().type == TokenType.COMMA:
                self.advance()
                continue
            
            ot = self.current()
            if ot.type == TokenType.REGISTER:
                operands.append(ot.value)
                operand_types.append('reg')
                self.advance()
            elif ot.type == TokenType.IMMEDIATE:
                operands.append(ot.value)
                operand_types.append('imm')
                self.advance()
            elif ot.type == TokenType.LABEL_REF:
                operands.append(ot.value)
                operand_types.append('label')
                self.advance()
        
        return InstructionNode(
            type="instruction", line=t.line,
            opcode=opcode, operands=operands, operand_types=operand_types
        )


class Validator:
    """Validate AST against opcode signatures."""
    
    def __init__(self, program: ProgramNode):
        self.program = program
        self.errors: List[str] = []
    
    def validate(self) -> bool:
        for node in self.program.instructions:
            if isinstance(node, InstructionNode):
                self._validate_instruction(node)
        return len(self.errors) == 0
    
    def _validate_instruction(self, node: InstructionNode):
        sig = SIGNATURES.get(node.opcode)
        if sig is None:
            self.errors.append(f"Line {node.line}: Unknown opcode '{node.opcode}'")
            return
        
        if len(node.operands) != len(sig):
            self.errors.append(
                f"Line {node.line}: '{node.opcode}' expects {len(sig)} operands, got {len(node.operands)}"
            )
            return
        
        for i, (actual, expected) in enumerate(zip(node.operand_types, sig)):
            if actual != expected and actual != 'label':
                self.errors.append(
                    f"Line {node.line}: '{node.opcode}' operand {i+1}: expected {expected}, got {actual}"
                )


# ── Tests ──────────────────────────────────────────────

import unittest


class TestLexer(unittest.TestCase):
    def test_simple(self):
        tokens = Lexer("HALT").tokens
        ops = [t for t in tokens if t.type == TokenType.OPCODE]
        self.assertEqual(len(ops), 1)
        self.assertEqual(ops[0].value, 'HALT')
    
    def test_register(self):
        tokens = Lexer("MOVI R0, 42").tokens
        regs = [t for t in tokens if t.type == TokenType.REGISTER]
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0].value, 'R0')
    
    def test_immediate(self):
        tokens = Lexer("MOVI R0, -5").tokens
        imms = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        self.assertEqual(len(imms), 1)
        self.assertEqual(imms[0].value, '-5')
    
    def test_hex_immediate(self):
        tokens = Lexer("MOVI R0, 0xFF").tokens
        imms = [t for t in tokens if t.type == TokenType.IMMEDIATE]
        self.assertEqual(imms[0].value, '0xFF')
    
    def test_label(self):
        tokens = Lexer("loop:").tokens
        labels = [t for t in tokens if t.type == TokenType.LABEL_DEF]
        self.assertEqual(len(labels), 1)
        self.assertEqual(labels[0].value, 'loop:')
    
    def test_comment(self):
        tokens = Lexer("; this is a comment").tokens
        comments = [t for t in tokens if t.type == TokenType.COMMENT]
        self.assertEqual(len(comments), 1)
    
    def test_multiline(self):
        tokens = Lexer("MOVI R0, 10\nADD R0, R0, R1\nHALT").tokens
        ops = [t for t in tokens if t.type == TokenType.OPCODE]
        self.assertEqual(len(ops), 3)


class TestParser(unittest.TestCase):
    def test_halt(self):
        tokens = Lexer("HALT").tokens
        parser = Parser(tokens)
        program = parser.parse()
        instrs = [n for n in program.instructions if isinstance(n, InstructionNode)]
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].opcode, 'HALT')
    
    def test_movi(self):
        tokens = Lexer("MOVI R0, 42").tokens
        parser = Parser(tokens)
        program = parser.parse()
        instrs = [n for n in program.instructions if isinstance(n, InstructionNode)]
        self.assertEqual(instrs[0].operands, ['R0', '42'])
    
    def test_label(self):
        tokens = Lexer("loop: INC R0").tokens
        parser = Parser(tokens)
        program = parser.parse()
        self.assertIn('loop', program.labels)
    
    def test_three_operand(self):
        tokens = Lexer("ADD R2, R0, R1").tokens
        parser = Parser(tokens)
        program = parser.parse()
        instrs = [n for n in program.instructions if isinstance(n, InstructionNode)]
        self.assertEqual(instrs[0].operands, ['R2', 'R0', 'R1'])
    
    def test_full_program(self):
        src = "MOVI R0, 10\nloop: DEC R0\nJNZ R0, -4\nHALT"
        tokens = Lexer(src).tokens
        parser = Parser(tokens)
        program = parser.parse()
        instrs = [n for n in program.instructions if isinstance(n, InstructionNode)]
        self.assertEqual(len(instrs), 4)


class TestValidator(unittest.TestCase):
    def test_valid_halt(self):
        tokens = Lexer("HALT").tokens
        program = Parser(tokens).parse()
        v = Validator(program)
        self.assertTrue(v.validate())
    
    def test_valid_add(self):
        tokens = Lexer("ADD R2, R0, R1").tokens
        program = Parser(tokens).parse()
        v = Validator(program)
        self.assertTrue(v.validate())
    
    def test_invalid_operand_count(self):
        tokens = Lexer("ADD R0").tokens
        program = Parser(tokens).parse()
        v = Validator(program)
        self.assertFalse(v.validate())
    
    def test_all_opcodes_defined(self):
        self.assertEqual(len(SIGNATURES), len(OPCODES))


if __name__ == "__main__":
    unittest.main(verbosity=2)
