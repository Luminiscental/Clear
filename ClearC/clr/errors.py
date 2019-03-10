"""
This module provides error types/functions for reporting errors when compiling Clear programs.
"""


class ClrCompileError(Exception):
    """
    This custom exception type is used to report compile errors when compiling Clear programs.
    """


def emit_error(message):
    """
    This function returns a function that can be called to emit
    a compile error with the given message.
    """

    def emission(*a, **kw):
        raise ClrCompileError(message)

    return emission


def parse_error(message, parser):
    """
    This function takes a message and a parser instance and appends the parser's
    current info to the message before passing on to emit_error.
    """
    return emit_error(message + f" {parser.current_info()}")
