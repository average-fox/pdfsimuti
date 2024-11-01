import typer
import fitz # fitz is actually PyMuPDF
import magic
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


def getFileType(filename):
    return filename.lower().split('.')[-1]


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
            if os.getcwd() != outputFileFolder and outputFileFolder != "": # No need to delete a directory over '' which is the working directory
                print(f"Cleaning created directory...{outputFileFolder}")
                os.rmdir(outputFileFolder)
        except Exception as e:
            print(e)
        raise typer.Abort()
    return True

def validateListForPDF(items, mimeCheck):
    # WARNING: If the list contains an item that was a merged pdf before, the list will include that item as well. Use exclude option to fix this.
    # TODO: Add a new option to merge called "exclude" which contains a list of excluded items from target list. Also make sure it doesn't throwback any errors.
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

def validateWorkingDirectory(target_file_path):
    """
    Validation of the folder path
    Checks if a folder path exists.
    If it doesn't, then create a folder for that path. Otherwise, the working script directory will be the saving folder path.
    If the folder path exists then the target folder path will be the saving folder path.

    Returns a validated folder path as str
    """
    trueFolderPath = os.path.dirname(target_file_path) # in case someone throws a directory of a file
    doesPathExist = os.path.isdir(trueFolderPath)

    if not doesPathExist:
        folder_creation_choice = typer.confirm(f"Warning! folder path {trueFolderPath} doesn't exist\nDo you wish to create it?")
        if folder_creation_choice:
            os.makedirs(trueFolderPath, exist_ok=True)
        else:
            print("Custom folder path creation aborted. Working directory will be the saving directory")
            trueFolderPath = os.getcwd()

    return trueFolderPath


def validateOverWrite(target_dir):
    filename = os.path.basename(target_dir)
    if os.path.exists(target_dir):
        return typer.confirm(f"{filename} already exists. Do you want to overwrite this file?")
    return False


def validateFileName(target_file_path):
    """
    Checks the filetype of the target directory filename.
    this will keep causing a prompt if the filetype doesn't match the correct type or the filename is SUS.
    """
    filename = os.path.basename(target_file_path)
    folderpath = os.path.dirname(target_file_path)
    while True:
        # if file is not a pdf format
        # WARNING: If filename is only 'pdf' then it will pass the checks. That is not accepted. Solution: Advanced search using mimetypes
        if getFileType(filename) != "pdf":
            print(f"Invalid FileType name. Expected 'pdf'. Got {getFileType(filename)}")
            filename = typer.prompt("Enter saving filename: ")
            continue

        elif os.path.exists(os.path.join(folderpath, filename)):
            # if the output already leads to an existing file and then user doesn't want to overwrite so they add another file
            #  and AGAIN make the same mistake like before, prompt them again!
            print("Changed file name already exists")
            if not validateOverWrite(os.path.join(folderpath, filename)):
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break
    return os.path.basename(filename)


def validateOutputFileName(file_target_path):
    """Extensive output file validation checker. Checks for filename first, then folder

    Args:
        file_target_path (str): Directory address of the saving file on system

    Returns:
        str: validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    # Otherwise, saving directory will say "" in confirmTask()
    folder_path = os.getcwd() if os.path.dirname(file_target_path) == "" else os.path.dirname(file_target_path)
    final_filename = ""
    while True:
        final_filename = validateFileName(file_target_path)
        working_dir = validateWorkingDirectory(os.path.join(folder_path, final_filename))

        break
    return os.path.join(working_dir, final_filename)


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

    validated_output_filename = ""
    if output != "merged.pdf":
        validated_output_filename = validateOutputFileName(output)

    # In case that the user passes --mimecheck after --output and not adding anything
    # For example: pdfsimuti merge . --output --mimecheck
    elif output == "--mimecheck":
        raise typer.BadParameter("--output takes no option. What are you doing?")
    else:
        validated_output_filename = "merged.pdf"

    if confirmTask(accepted_file_list, validated_output_filename):
        merge_runtime(accepted_file_list, validated_output_filename)
