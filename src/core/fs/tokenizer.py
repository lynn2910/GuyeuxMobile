from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class TokenType(Enum):
    """
    Defines the different types of tokens that can be found in the .map file.
    These represent the keywords, symbols, and literals of the custom language.
    """
    # Section keywords
    GRAPH = "GRAPH"
    SIMULATION = "SIMULATION"
    VEHICLES = "VEHICLES"  # Alias for SIMULATION
    SPAWNERS = "SPAWNERS"
    INTERSECTIONS = "INTERSECTIONS"

    # Object definition keywords
    NODE = "NODE"
    UEDGE = "UEDGE"  # Unidirectional edge
    BEDGE = "BEDGE"  # Bidirectional edge
    CAR = "CAR"
    SPAWNER = "SPAWNER"
    TRAFFIC_LIGHT = "TRAFFIC_LIGHT"

    # Punctuation and operators
    LPAREN = "LPAREN"        # (
    RPAREN = "RPAREN"        # )
    COLON = "COLON"          # :
    COMMA = "COMMA"          # ,
    EQUALS = "EQUALS"        # =

    # Literals and identifiers
    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"

    # Control tokens
    EOF = "EOF"              # End of File
    NEWLINE = "NEWLINE"      # \n


@dataclass
class Token:
    """
    Represents a single token identified by the Tokenizer.
    It contains the token's type, its value, and its position in the source file.
    """
    type: TokenType
    value: any
    line: int
    column: int


class Tokenizer:
    """
    Scans the raw text content of a .map file and converts it into a sequence of tokens.
    This process, also known as lexical analysis, is the first step in parsing the file.
    """
    def __init__(self, content: str):
        self.content = content
        self.pos = 0
        self.line = 1
        self.column = 1
        self.tokens = []

    def current_char(self) -> Optional[str]:
        """Returns the character at the current position, or None if at the end."""
        if self.pos >= len(self.content):
            return None
        return self.content[self.pos]

    def peek_char(self, offset: int = 1) -> Optional[str]:
        """Looks at a character ahead of the current position without advancing."""
        pos = self.pos + offset
        if pos >= len(self.content):
            return None
        return self.content[pos]

    def advance(self):
        """
        Moves the current position forward by one character.
        Updates line and column counters.
        """
        if self.pos < len(self.content):
            if self.content[self.pos] == '\n':
                self.line += 1
                self.column = 1
            else:
                self.column += 1
            self.pos += 1

    def skip_whitespace(self):
        """Advances past any space or tab characters."""
        while self.current_char() in [' ', '\t', '\r']:
            self.advance()

    def read_number(self) -> Token:
        """Reads a sequence of digits (and optionally a decimal point) into a NUMBER token."""
        start_col = self.column
        num_str = ""
        has_dot = False

        # Handle negative numbers
        if self.current_char() == '-':
            num_str += '-'
            self.advance()

        while self.current_char() and (self.current_char().isdigit() or self.current_char() == '.'):
            if self.current_char() == '.':
                if has_dot:  # A number can't have two decimal points
                    break
                has_dot = True
            num_str += self.current_char()
            self.advance()

        value = float(num_str) if has_dot else int(num_str)
        return Token(TokenType.NUMBER, value, self.line, start_col)

    def read_identifier(self) -> Token:
        """Reads a sequence of alphanumeric characters into an IDENTIFIER or keyword token."""
        start_col = self.column
        ident = ""

        while self.current_char() and (self.current_char().isalnum() or self.current_char() == '_'):
            ident += self.current_char()
            self.advance()

        # Check if the identifier is a reserved keyword.
        keywords = {
            "GRAPH": TokenType.GRAPH,
            "NODE": TokenType.NODE,
            "UEDGE": TokenType.UEDGE,
            "BEDGE": TokenType.BEDGE,
            "SIMULATION": TokenType.SIMULATION,
            "VEHICLES": TokenType.VEHICLES,
            "CAR": TokenType.CAR,
            "SPAWNERS": TokenType.SPAWNERS,
            "SPAWNER": TokenType.SPAWNER,
            "INTERSECTIONS": TokenType.INTERSECTIONS,
            "TRAFFIC_LIGHT": TokenType.TRAFFIC_LIGHT,
        }

        token_type = keywords.get(ident, TokenType.IDENTIFIER)
        return Token(token_type, ident, self.line, start_col)

    def tokenize(self) -> List[Token]:
        """
        Processes the entire input string and returns a list of all identified tokens.
        """
        while self.current_char():
            self.skip_whitespace()

            if not self.current_char():
                break

            char = self.current_char()
            col = self.column

            # Main tokenizing logic: check the current character to decide the token type.
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
            elif char == '=':
                self.tokens.append(Token(TokenType.EQUALS, '=', self.line, col))
                self.advance()
            elif char.isdigit() or (char == '-' and self.peek_char() and self.peek_char().isdigit()):
                self.tokens.append(self.read_number())
            elif char.isalpha() or char == '_':
                self.tokens.append(self.read_identifier())
            else:
                raise SyntaxError(f"Unexpected character '{char}' at line {self.line}, column {col}")

        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        return self.tokens
