"""
Definitions for compile errors and tracking/displaying them.
"""

from typing import List, NamedTuple


class CompileError(NamedTuple):
    """
    Class representing a compile error, has a message and a region of code.
    """

    message: str
    regions: List["SourceView"]

    def display(self) -> str:
        """
        Returns a string representation of the error.
        """
        # TODO: Line number, context, e.t.c.
        return f"{self.message}: {self.regions}"


class ErrorTracker:
    """
    Wrapper class for keeping track of a list of errors.
    """

    def __init__(self) -> None:
        self._errors: List[CompileError] = []

    def add(self, message: str, regions: List["SourceView"]) -> None:
        """
        Add a new error.
        """
        self._errors.append(CompileError(message, regions))

    def get(self) -> List[CompileError]:
        """
        Gets the list of errors.
        """
        return self._errors


class IncompatibleSourceError(Exception):
    """
    Custom exception for when source views expected to have the same source have different sources.
    """


class SourceView:
    """
    Represents a region within a Clear source string.
    """

    def __init__(self, source: str, start: int, end: int) -> None:
        self.start = start
        self.end = end
        self.source = source

    def __repr__(self) -> str:
        return f"SourceView[{str(self)}]"

    def __str__(self) -> str:
        return self.source[self.start : self.end + 1]

    @staticmethod
    def all(source: str) -> "SourceView":
        """
        Given a source string returns a view of the entire string.
        """
        return SourceView(source=source, start=0, end=len(source) - 1)

    @staticmethod
    def range(start: "SourceView", end: "SourceView") -> "SourceView":
        """
        Takes a start and end view and returns a view of the whole range between them.
        If they view separate sources raises an IncompatibleSourceError.
        """
        if start.source != end.source:
            raise IncompatibleSourceError()
        return SourceView(source=start.source, start=start.start, end=end.end)
