
class ClrCompileError(Exception):

    pass

def emit_error(message, dis=False):

    def emission(*a, **kw):
        raise ClrCompileError(message)
    return emission
