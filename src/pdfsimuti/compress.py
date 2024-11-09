import typer
# import magic
# import os

from typing_extensions import Annotated

app = typer.Typer()

def validatePDFfile(itemPDF, mimecheck) -> bool:
    pass

def confirm(itemPDF) -> bool:
    pass

def compress_runtime(item):
    pass

def compress(
        item: Annotated[str, typer.Argument(help="PDF files to be compressed")],
        mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=False,
):
    pass
