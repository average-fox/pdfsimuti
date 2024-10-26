import typer
import fitz # fitz is actually PyMuPDF
import magic
import os
from os import path
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
    A very simple PDF utility tool written in Python using Typer.
    """


def exit(code):
    if code == 1:
        raise typer.Exit(code=code)
    raise typer.Exit()



def validateListForPDF(items, mimeCheck):
    """
    Accepts LIST required, BOOL optional.
    Appends the accepted files into another list. Returns a list of validated files.
    1. item must be a path in existence.
    2. item cannot be a directory. This function only accepts files.
    3. item must end with .pdf as format.
    4. Accepted list must be greater than 1.
    5. (optional) Item will be checked with mimecheck if passed
    """
    list_items=[]
    for item in items:
        if not os.path.isdir(item) and os.path.exists(item) and item.lower().split(".")[-1] == "pdf":
            list_items.append(item)

    if mimeCheck:
        for item in list_items:
            if magic.detect_from_filename(item).mime_type != "application/pdf":
                print(f"Caution! Automatic Ignore. {item} is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'")
                list_items.remove(item)

    if len(list_items) <= 1:
        typer.echo(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")
        exit(1)
    
    return list_items


def merge_runtime(input_files):
    """
    Takes a LIST of the compatible target PDFs and merge them.
    The list must be validated beforehand.
    """
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save("merged.pdf")
        print("File Saved as merged.pdf")
    except Exception as e: print(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode.")



@app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF.")
def merge(items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths. Tip: Pass '.' to include current directory.")],
          mimeCheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check.")]=False):
    """
    Main function for the merge function.
    Accepts a required argument that automatically gets turned into a list if more of the arguments were passed.
    Contains an optional mimecheck as bool for enabling mimecheeck functionality.
    """
    for item in items:
        if item == ".": 
            items.extend(os.listdir(os.getcwd())) # Adds two lists into 1
    merge_runtime(validateListForPDF(items, mimeCheck=mimeCheck))


