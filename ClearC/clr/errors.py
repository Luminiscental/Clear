class ClrCompileError(Exception):
    pass


def emit_error(message):
    def emission(*a, **kw):
        raise ClrCompileError(message)

    return emission


def parse_error(message, parser):
    return emit_error(message + f" {parser.current_info()}")
