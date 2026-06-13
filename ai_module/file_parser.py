from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


def parse_file(file_path):
    """
    Extract text from PDF or TXT files.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found")

    suffix = path.suffix.lower()

    # TXT files
    if suffix == ".txt":
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    # PDF files
    if suffix == ".pdf":

        if PdfReader is None:
            raise ImportError(
                "Install pypdf using:\n"
                "pip install pypdf"
            )

        text = ""

        reader = PdfReader(file_path)

        for page in reader.pages:

            page_text = page.extract_text()

            if page_text:
                text += page_text + "\n"

        return text

    raise ValueError(
        "Supported formats are .pdf and .txt only"
    )