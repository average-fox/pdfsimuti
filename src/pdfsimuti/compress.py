import typer
# import magic
import fitz
import os

from typing_extensions import Annotated
from typing import List

app = typer.Typer()


def getFileType(filename):
    """
    Returns the filetype by checking if it endswith .pdf
    """
    return filename.lower().split(".")[-1]


def validateListForPDF(itemPDF, mimecheck=False):
    valid_list = [os.path.abspath(item) for item in itemPDF if (getFileType(item) == "pdf" and os.path.exists(item))]
    return valid_list
    

def confirm(itemPDF) -> bool:
    pass

def compressPdf(itemList):
    for item in itemList:
        with fitz.open(item) as doc:
            doc.save("converted.pdf", garbage=4, deflate=True)
    

def display_after_actions_report(): pass

def compress_runtime(itemList):
    valid_list = validateListForPDF(itemList)
    compressPdf(valid_list)

def compress(
        item: Annotated[List[str], typer.Argument(help="PDF files to be compressed")],
        mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=False,
):
    compress_runtime(item)

