import typer
import fitz # fitz is actually PyMuPDF
import magic
from os import path
import os
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
    list_items=[]
    for item in items:
        if not os.path.isdir(item) and os.path.exists(item) and item.lower().split(".")[-1] == "pdf":
            list_items.append(item)

    if mimeCheck:
        for item in list_items:
            if magic.detect_from_filename(item).mime_type != "application/pdf":
                print(f"Caution! {item} is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'")
                list_items.remove(item)

    if len(list_items) <= 1:
        typer.echo(f"Excepted more than 1 compatible file for merging.")
        exit(1)

    return list_items


def merge_runtime(input_files):
    """
    Takes a LIST of the target PDFs and merge them
    """
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save("merged.pdf")
    except Exception as e: print(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode.")



@app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF.")
def merge(items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths. Tip: Pass '.' to include current directory.")],
          mimeCheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check.")]=False):
    """
    main function for the merge function.
    """
    for item in items:
        if item == ".": 
            items.remove(".") # remove . because we don't need it in our list
            items.extend(os.listdir(os.getcwd())) # Adds two lists into 1
    
    merge_runtime(validateListForPDF(items, mimeCheck=mimeCheck))


