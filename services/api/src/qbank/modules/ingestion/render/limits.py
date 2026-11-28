"""The limits of rendering a document (M6 design note §6, threat model U2 to U4, U6)."""

MAX_PAGES = 200
MAX_SOURCE_PIXELS = 40_000_000  # a picture's width x height, read from its header before decoding
PAGE_MAX_SIDE = 2200  # longest side of a page picture, in pixels
THUMB_SIDE = 320
JPEG_QUALITY = 88
MAX_PAGE_POINTS = 14_400  # a PDF page larger than 200 inches a side is not a page of a paper
RENDER_SECONDS = 300  # wall-clock time for one file; checked between pages
MAX_TEXT_CHARS = 20_000  # of text kept per page

# Word files (a ZIP of XML parts), read in memory and never unpacked to disk
DOCX_MAX_PARTS = 500
DOCX_MAX_UNPACKED = 100 * 1024 * 1024  # declared, all parts together
DOCX_MAX_XML = 10 * 1024 * 1024  # the document part itself (read whole, so kept small)
DOCX_MAX_ELEMENTS = 3_000_000
DOCX_MAX_FIGURES = 30
DOCX_PAGE_CHARS = 3_000  # a page of a Word file is a run of paragraphs about this long
