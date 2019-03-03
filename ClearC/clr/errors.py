class ClrCompileError(Exception):

    pass


def emit_error(message):
    def emission(*a, **kw):
        raise ClrCompileError(message)

    return emission
