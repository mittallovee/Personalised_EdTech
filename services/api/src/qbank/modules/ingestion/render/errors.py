"""How rendering fails. The code is stored on the file; no text of the document ever is."""


class RenderError(Exception):
    """A document (or one page of it) could not be turned into pages. ``code`` is what is stored."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
