import typer
import fitz # fitz is actually PyMuPDF
import magic
import os.path
from typing import List # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated


app = typer.Typer(
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    rich_markup_mode="rich"
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
    # If File doesn't exists in address, stop.
    if not os.path.exists(item):
        typer.echo(f"Error: {item} doesn't exist.")
        return False

    # If File isn't PDF by filename.filetype, stop
    item_type = item.lower().split('.')[-1]
    if item_type != 'pdf': 
        typer.echo(f"Error: {item} has wrong filetype. Expected: 'pdf' Got '{item_type}'.")
        return False
   
    # If mimeCheck is passed, python-magic(magic) lib will check for the item's mimeType to be 'application/pdf' negatively
    if mimeCheck:
        if not magic.detect_from_filename(item).mime_type == 'application/pdf':
            print(f"Error! {item} is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'")
            return False

    return True
    

def merge_runtime(input_files):
    """
    Takes a LIST of the target PDFs and merge them
    """
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save("merged.pdf")
    except Exception as e: print(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimeCheck mode.")



@app.command(
    help="Merges [italic]n[/italic] number of PDFs into a super PDF")
def merge(items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths.")],
          mimeCheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check.")]=False):
    """
    main function for the merge function.
    """
    # Check if number of items as PDF arguments is more than 1.
    # You need at least 2 PDFs to merge
    if len(items) <= 1: 
        typer.echo(f"Excepted more than 1 file for Merging.")
        exit(1)
    
    # Check each of the arguments to see if they are actually PDFs negatively.
    for item in items:
        if not checkIfPDF(item, mimeCheck=mimeCheck): exit(1)
    
    # Pass list to merge function
    merge_runtime(items)



