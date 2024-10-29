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

    print(f"\nThe following files will be merged: {itemsList}. \nOutput file is: {os.path.basename(outputFileName)}\nSaving directory is: {os.path.dirname(outputFileName)}\nEstimated Size: More than{fileSize: .2f} MB\n")
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
        raise typer.BadParameter(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")
    
    return list_items


# TODO: Make the entire project determine if the output file exists in nature or not. If it exists, warn for replacing or not.
def validateOutputFileName(filename):
    folder_path = os.path.dirname(filename)
    file_path_exists = os.path.isdir(os.path.dirname(filename))
    fileType = filename.lower().split('.')[-1]
    
    while True:
        print(f"\n{filename} is not a valid filename.")

        if not file_path_exists and fileType != "pdf":
            raise typer.BadParameter(f"Critical. Folder path doesn't exist. \nAdditionally, filetype is invalid. Expected 'pdf' Got '{fileType}'")

        if not file_path_exists:
            choice = typer.confirm(f"\nThe folder ({folder_path}) you given as output doesn't exist. \nDo you wish to create it?")
            if choice: 
                os.makedirs(folder_path, exist_ok=True)

        # BUG: If the user creates a directory, the file should be saved inside that directory. However, this code allows the file to be saved elsewhere.
        # That means: This feature is useless and not properly utilized.
        if fileType != "pdf":
            filename = typer.prompt("Enter output location: ")

        break
    return filename


def merge_runtime(input_files, outputFileName):
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save(outputFileName)
        print(f"File Saved as {outputFileName}")
    except RuntimeError: # If output directory specified doesn't exist 
        print("Housten, We ... got a problem")
        print(Tools.mupdf_warnings())
        # raise typer.BadParameter(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode. \nIt will ignore all files that are not PDF by mime.")


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

