import typer
import fitz # fitz is actually PyMuPDF
import magic
import os.path
from typing import List
from typing_extensions import Annotated


app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_show_locals=False
)

@app.callback()
def callback():
    """
    A very simple PDF utility tool written in Python using Typer
    """


def exit(code):
    if code == 1:
        raise typer.Exit(code=code)
    raise typer.Exit()


def checkIfPDF(item, mimeCheck):
    """
    1. Checks for the file's existence using os.path
    2. Takes arg(item), splits it by '.' and checks for .pdf existence
    3. If mimeCheck is True, runs a mime_type check on the item
    """
    # Check if File exists
    if not os.path.exists(item):
        typer.echo(f"Error: {item} doesn't exist.")
        return False

    # Check if File is PDF
    item_type = item.lower().split('.')[-1]
    if item_type != 'pdf': 
        typer.echo(f"Error: {item} has wrong filetype. Expected 'pdf' Got '{item_type}'.")
        return False
   
    # If mimeCheck is passed, magic lib will check for the item's mimeType to be 'application/pdf'
    if mimeCheck:
        if not magic.detect_from_filename(item).mime_type == 'application/pdf':
            print(f"Error! {item} is not an PDF. Expected: 'application/pdf'. Got: {magic.from_file(item)}")
            return False

    return True
    

def merge_runtime(input_files):
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save("merged.pdf")
    except Exception as e: print(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimeCheck mode.")



@app.command()
def merge(items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths.")],
          mimeCheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check.")]=False):
    """
    Merge 2 PDFs or more into a super PDF
    """
    # Check if number of items as PDF arguments is more than 1.
    if len(items) <= 1: 
        typer.echo(f"Excepted more than 1 file for Merging.")
        exit(1)
    
    # Check each of the arguments to see if they are actually PDFs.
    for item in items:
        if not checkIfPDF(item, mimeCheck=mimeCheck): exit(1)

    
    # Pass list to merge function
    merge_runtime(items)



