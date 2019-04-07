class ClrCompileError(Exception):
    pass


def emit_error(message):
    def emission(*a, **kw):
        raise ClrCompileError(message)

    return emission


def parse_error(message, parser):
    return emit_error(message + f" {parser.current_info()}")


def sync_errors(accept_func):
    def synced(self, visitor):
        try:
            accept_func(self, visitor)
        except ClrCompileError as error:
            visitor.errors.append(str(error))

    return synced
