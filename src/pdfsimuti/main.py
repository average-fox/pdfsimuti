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


def confirmTask(itemsList, outputFileName):
    fileSize = 0
    for i in itemsList:
        fileSize+=(os.path.getsize(i) / (1024*1024))

    print(f"\nThe following files will be merged: {itemsList}. \nOutput file is: {outputFileName} \nEstimated Size: More than {fileSize: .2f} MB\n")
    choice = typer.confirm("Are you certain you want to continue?")
    if not choice:
        raise typer.Abort()
    return True


def validateListForPDF(items, mimeCheck):
    list_items=[]
    for item in items:
        if not os.path.isdir(item) and os.path.exists(item) and item.lower().split(".")[-1] == "pdf":
            list_items.append(item)

    if mimeCheck:
        print("\nmimecheck is enabled.")
        for item in list_items:
            if magic.detect_from_filename(item).mime_type != "application/pdf":
                print(f"Caution! Automatic Ignore. {item} is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'")
                list_items.remove(item)

    if len(list_items) <= 1:
        raise typer.BadParameter(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.\n")
    
    return list_items


# TODO: Make the entire project determine if the output file exists in nature or not. If it exists, warn for replacing or not.
def validateOutputFileName(filename):
    while filename.lower().split('.')[-1] != "pdf":
        print(f"{filename} is not a valid filename.")
        filename = typer.prompt("Enter Output Name: ")
    return filename


def merge_runtime(input_files, outputFileName):
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save(outputFileName)
        print(f"File Saved as {outputFileName}")
    except Exception as e: 
        raise typer.BadParameter(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode. \nIt will ignore all files that are not PDF by mime.")


@app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF.")
def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths. Tip: Pass '.' to include current directory.")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check. Files that failed the check will be removed from selection.")]=False,
    output: Annotated[str, typer.Option(help="Save ouutput file name. Can Accept a folder directory as well.")]="merged.pdf"):
    for item in items:
        if item == ".": 
            items.extend(os.listdir(os.getcwd())) # Adds two lists into 1
    
    if output != "merged.pdf": output = validateOutputFileName(output)
    accepted_file_list = validateListForPDF(items, mimecheck)
    if confirmTask(accepted_file_list, output): merge_runtime(accepted_file_list, output)

