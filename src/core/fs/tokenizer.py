from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class TokenType(Enum):
    GRAPH = "GRAPH"
    NODE = "NODE"

    UEDGE = "UEDGE"
    BEDGE = "BEDGE"

    SIMULATION = "SIMULATION"
    CAR = "CAR"

    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    COLON = "COLON"
    COMMA = "COMMA"

    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"

    EOF = "EOF"
    NEWLINE = "NEWLINE"


@dataclass
class Token:
    type: TokenType
    value: any
    line: int
    column: int


class Tokenizer:
    def __init__(self, content: str):
        self.content = content
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def current_char(self) -> Optional[str]:
        if self.pos >= len(self.content):
            return None
        return self.content[self.pos]

    def peek_char(self, offset: int = 1) -> Optional[str]:
        pos = self.pos + offset
        if pos >= len(self.content):
            return None
        return self.content[pos]

    def advance(self):
        if self.pos < len(self.content):
            if self.content[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def skip_whitespace(self):
        while self.current_char() in [' ', '\t', '\r']:
            self.advance()

    def read_number(self) -> Token:
        start_col = self.column
        num_str = ""
        has_dot = False

        if self.current_char() == '-':
            num_str += '-'
            self.advance()

        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                if has_dot:
                    break
                has_dot = True
            num_str += self.current_char()
            self.advance()

        value = float(num_str) if has_dot else int(num_str)
        return Token(TokenType.NUMBER, value, self.line, start_col)

    def read_identifier(self) -> Token:
        start_col = self.column
        ident = ""

        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            ident += self.current_char()
            self.advance()

        keywords = {
            "GRAPH": TokenType.GRAPH,
            "NODE": TokenType.NODE,
            "UEDGE": TokenType.UEDGE,
            "BEDGE": TokenType.BEDGE,
            "SIMULATION": TokenType.SIMULATION,
            "CAR": TokenType.CAR,
        }

        token_type = keywords.get(ident, TokenType.IDENTIFIER)
        return Token(token_type, ident, self.line, start_col)

    def tokenize(self) -> List[Token]:
        while self.current_char():
            self.skip_whitespace()

            if not self.current_char():
                break

            char = self.current_char()
            col = self.column

            if char == '\n':
                self.tokens.append(Token(TokenType.NEWLINE, '\n', self.line, col))
                self.advance()
            elif char == '(':
                self.tokens.append(Token(TokenType.LPAREN, '(', self.line, col))
                self.advance()
            elif char == ')':
                self.tokens.append(Token(TokenType.RPAREN, ')', self.line, col))
                self.advance()
            elif char == ':':
                self.tokens.append(Token(TokenType.COLON, ':', self.line, col))
                self.advance()
            elif char == ',':
                self.tokens.append(Token(TokenType.COMMA, ',', self.line, col))
                self.advance()
            elif char.isdigit() or (char == '-' and self.peek_char() and self.peek_char().isdigit()):
                self.tokens.append(self.read_number())
            elif char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
            else:
                raise SyntaxError(f"Caractère inattendu '{char}' à la ligne {self.line}, colonne {col}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
