import typer
import fitz # fitz is actually PyMuPDF
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


def checkIfPDF(item):
    """
    1. Checks for the file's existence using os.path
    2. Takes arg(item), splits it by '.' and checks for .pdf existence
    """
    # Check if File exists
    if not os.path.exists(item):
        typer.echo(f"Error: {item} doesn't exist")
        return False

    # Check if File is PDF
    if item.lower().split('.')[-1] != 'pdf': 
        typer.echo(f'Error: {item} has wrong filetype')
        return False
    
    return True
    

def merge_runtime(input_files):
    doc = fitz.open()
    for input_file in input_files:
        doc.insert_file(input_file)
    doc.save("merged.pdf")


@app.command()
def merge(items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths.")]):
    """
    Merge 2 PDFs or more into a super PDF
    """
    # Check if number of items as PDF arguments is more than 1.
    if len(items) <= 1: 
        typer.echo(f"Excepted more than 1 file for Merging")
        exit(1)
    
    # Check each of the arguments to see if they are actually PDFs.
    for item in items:
        if not checkIfPDF(item): exit(1)

    # Pass list to merge function
    merge_runtime(items)



