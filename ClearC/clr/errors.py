
class ClrDisassembleError(Exception):

    pass

class ClrCompileError(Exception):

    pass

def emit_error(message, dis=False):

    def emission():
        if dis:
            raise ClrDisassembleError(message)
        else:
            raise ClrCompileError(message)
    return emission
