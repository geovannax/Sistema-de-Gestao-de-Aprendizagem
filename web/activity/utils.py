"""Utilitários do app activity."""
from __future__ import annotations

from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token

_LANGUAGE_MAP: dict[str, str] = {
    'python': 'python3',
    'javascript': 'javascript',
    'java': 'java',
    'c': 'c',
    'cpp': 'cpp',
}


def normalize_code(code: str, language: str) -> str:
    """Normaliza código removendo espaços e comentários via tokenização.

    Usa ``pygments`` para tokenizar e filtrar tokens de whitespace e
    comentários, permitindo comparação agnóstica a formatação entre a
    resposta do aluno e o gabarito de exercícios de completar código.

    Args:
        code: Código-fonte a normalizar.
        language: Linguagem do código (``'python'``, ``'javascript'``,
            ``'java'``, ``'c'`` ou ``'cpp'``).

    Returns:
        String com apenas os tokens significativos concatenados,
        sem espaços ou comentários.

    Example:
        >>> normalize_code('x  =  1', 'python') == normalize_code('x=1', 'python')
        True
    """
    lexer_name = _LANGUAGE_MAP.get(language, 'text')
    try:
        lexer = get_lexer_by_name(lexer_name)
    except Exception:
        return ''.join(code.split())

    parts = []
    for ttype, val in lex(code, lexer):
        if ttype in Token.Comment:
            continue
        if ttype in Token.Text and val.strip() == '':
            continue
        parts.append(val)
    return ''.join(parts)
