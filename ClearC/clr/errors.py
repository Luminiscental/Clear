"""
Definitions for compile errors and tracking/displaying them.
"""

from typing import List, Tuple

import enum
import dataclasses as dc


class Severity(enum.Enum):
    """
    Enumerates the possible error severities.
    """

    NONE = 0
    WARNING = 1
    ERROR = 2

    def __lt__(self, other: "Severity") -> bool:
        return int(self.value) < int(other.value)

    def __le__(self, other: "Severity") -> bool:
        return int(self.value) <= int(other.value)

    def __gt__(self, other: "Severity") -> bool:
        return int(self.value) > int(other.value)

    def __ge__(self, other: "Severity") -> bool:
        return int(self.value) >= int(other.value)

    def __str__(self) -> str:
        return self.name


@dc.dataclass
class CompileError:
    """
    Class representing a compile error, has a message and a region of code.
    """

    message: str
    regions: List["SourceView"]
    severity: Severity = Severity.ERROR

    def __str__(self) -> str:
        line_number_width = len(str(max(region.endline() for region in self.regions)))
        # Separate regions with an ellipsis, in order of how early they start
        regions = "\n...\n".join(
            region.display(line_number_width)
            for region in sorted(self.regions, key=lambda region: region.start)
        )
        return f"[{self.severity}] {self.message}:\n\n{regions}"


@dc.dataclass
class ErrorTracker:
    """
    Wrapper class for keeping track of a list of errors.
    """

    _errors: List[CompileError] = dc.field(default_factory=list)

    def add(
        self,
        message: str,
        regions: List["SourceView"],
        severity: Severity = Severity.ERROR,
    ) -> None:
        """
        Add a new error.
        """
        self._errors.append(CompileError(message, regions, severity))

    def get(self) -> List[CompileError]:
        """
        Gets the list of errors.
        """
        return self._errors


class IncompatibleSourceError(Exception):
    """
    Custom exception for when source views expected to have the same source have different sources.
    """


@dc.dataclass
class SourceView:
    """
    Represents a region within a Clear source string.
    """

    source: str
    start: int
    end: int

    def __str__(self) -> str:
        return self.source[self.start : self.end]

    def endline(self) -> int:
        """
        Returns the line number of the last line spanned by this region.
        """
        return 1 + self.source[: self.end].count("\n")

    def display(self, line_number_width: int) -> str:
        """
        Display the region as a string with line numbers and underlines.
        """
        # List of (line number, line content, underline)
        lines: List[Tuple[int, str, str]] = []
        # Index into the source of the start of the current line
        index = 0
        for i, line in enumerate(self.source.splitlines(keepends=True)):
            if self.start < index + len(line):
                line_number = i + 1
                # Check if the self starts or ends on this line
                starts = self.start > index
                ends = self.end < index + len(line)
                # Find where in this line the self starts and ends
                start = self.start - index if starts else 0
                end = self.end - index if ends else len(line)
                # Add the information to the list
                # Subtract 1 from underline to avoid underlining \n
                lines.append((line_number, line, " " * start + "~" * (end - start - 1)))
                # Stop iterating if the error self ended
                if ends:
                    break
            index += len(line)
        # Padding for underlines which don't get numbers
        line_number_padding = " " * line_number_width
        return "\n".join(
            f"{line_number:{line_number_width}} | {line}"
            f"{line_number_padding} | {underline}"
            for line_number, line, underline in lines
        )

    @staticmethod
    def all(source: str) -> "SourceView":
        """
        Given a source string returns a view of the entire string.
        """
        return SourceView(source=source, start=0, end=len(source))

    @staticmethod
    def range(start: "SourceView", end: "SourceView") -> "SourceView":
        """
        Takes a start and end view and returns a view of the whole range between them.
        If they view separate sources raises an IncompatibleSourceError.
        """
        if start.source != end.source:
            raise IncompatibleSourceError
        return SourceView(source=start.source, start=start.start, end=end.end)
