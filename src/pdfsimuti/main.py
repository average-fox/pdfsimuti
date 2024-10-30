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
    outputFileFolder = os.path.dirname(outputFileName)
    fileSize = 0
    for i in itemsList:
        fileSize+=(os.path.getsize(i) / (1024*1024))

    print(f"\nThe following files will be merged: {itemsList}. \nOutput file is: {os.path.basename(outputFileName)}\nSaving directory is: {outputFileFolder}\nEstimated Size: More than{fileSize: .2f} MB\n")
    choice = typer.confirm("Are you certain you want to continue?")
    if not choice:
        # if user created the custom saving directory, delete the newly created directory.
        # It assumes that the saving directory is not the working directory.
        # Directories can be created from validateOutputFileName()
        try:
            if os.getcwd() != outputFileFolder:
                print("Cleaning created directory...")
                os.rmdir(outputFileFolder)
        except Exception as e:
            print(e)
        raise typer.Abort()
    return True


def validateListForPDF(items, mimeCheck):
    # WARNING: If the list contains an item that was a merged pdf before, the list will include that item as well.
    # TODO: Add a new option to merge called "exclude" which contains a list of excluded items from target list. Also, make sure it doesn't throwback any errors.
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


def validateOutputFileName(file_target_path):
    # if user passes . then the working directory will be folder path
    if os.path.dirname(file_target_path) == "": 
        folder_path = os.getcwd()
    else: folder_path = os.path.dirname(file_target_path)

    filename = os.path.basename(file_target_path)
    folder_path_exists = os.path.isdir(folder_path)
    file_path_exists = os.path.isdir(os.path.dirname(file_target_path))
    fileType = filename.lower().split('.')[-1]
    overwrite_file = False
    # In case that the user passes --mimecheck after --output and not adding anything
    # For example: pdfsimuti merge . --output --mimecheck
    if file_target_path == "--mimecheck":
        raise typer.BadParameter("--output takes no option. What are you doing?")

    while fileType != "pdf" or not file_path_exists:

        if not folder_path_exists:
            choice = typer.confirm(f"\nThe folder ({folder_path}) you given as output doesn't exist. \nDo you wish to create it?")
            if choice:
                os.makedirs(folder_path, exist_ok=True)
            else:
                print(f"Folder Creation ({folder_path}) is aborted. File will be saved in active directory")
                folder_path = os.getcwd()



        if os.path.exists(file_target_path): 
            print("Warning! file path exists")
            choice = typer.confirm("The saving directory already exists. Overwrite?")
            overwrite_file = True if choice else False
            print(overwrite_file)

        if fileType != "pdf" or not overwrite_file and os.path.exists(file_target_path):
            if fileType != "pdf": print(f"{filename} is not a PDF valid name. (i.e example.pdf)")
            elif os.path.exists(file_target_path) and not overwrite_file: print("You can't have exisitng files")
            
            filename = os.path.basename(typer.prompt("Enter output filename: "))
            if os.path.basename(filename).lower().split('.')[-1] != "pdf": 
                continue
        

        break
    return os.path.join(folder_path, filename)

def overwrite_list_if_occurance(target_list):
    pass


def merge_runtime(input_files, outputFileName):
    try:
        doc = fitz.open()
        for input_file in input_files:
            doc.insert_file(input_file)
        doc.save(outputFileName)
        print(f"File Saved as {outputFileName}")
    except Exception as e: # If output directory specified doesn't exist 
        raise typer.BadParameter(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode. \nIt will ignore all files that are not PDF by mime.")


@app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF.")
def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths. Tip: Pass '.' to include current directory.")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check. Files that failed the check will be removed from selection.")]=False,
    output: Annotated[str, typer.Option(help="Save output file name. Can Accept a folder directory as well.")]="merged.pdf"):
    for item in items:
        if item == ".": 
            items.extend(os.listdir(os.getcwd())) # Adds two lists into 1
    
    accepted_file_list = validateListForPDF(items, mimecheck)
    if output != "merged.pdf": validated_output_filename = validateOutputFileName(output)

    if confirmTask(accepted_file_list, validated_output_filename):
        merge_runtime(accepted_file_list, validated_output_filename)

