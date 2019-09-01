from typing_extensions import Protocol


class IWriter(Protocol):
    def write(self, s: str) -> None:
        ...
