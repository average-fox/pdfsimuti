import typer
import fitz  # fitz is actually PyMuPDF
import magic
import os
from typing import List  # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated

from rich.panel import Panel
from rich.console import Console

console = Console()
app = typer.Typer()
global_currentDirectory = os.getcwd() # use this var on functions that calls os.getcwd() more than once

def getFileType(filename):
    """
    Returns the filetype by checking if it endswith .pdf
    """
    return filename.lower().split(".")[-1]


def getFileBaseName(fileStr):
    """
    Returns the directory basename of the file
    """
    return os.path.basename(fileStr)


def getFileDirName(fileStr):
    """
    Returns the directory folder path of the file
    """
    return os.path.dirname(fileStr)


def returnStrPath(folderpath, filename):
    return os.path.join(folderpath, filename)


def confirmTask(itemsList, outputFileName, preserve_files):
    """
    Overview of the entire task before the start of the job
    """
    local_currentDirectory = global_currentDirectory

    outputFileFolder = local_currentDirectory if getFileDirName(outputFileName) == "" else getFileDirName(outputFileName)

    # Calculate estimated size of the merge
    fileSize = 0
    for i in itemsList:
        fileSize += os.path.getsize(i) / (1024 * 1024)

    console.print(Panel(f"""
[u]Files to be merged[/u]: {itemsList}
[u]Output file[/u]: {getFileBaseName(outputFileName)}
[u]Saving directory[/u]: {outputFileFolder}
[u]Estimated Size[/u]: >{fileSize: .2f} MB
    """, title="OVERVIEW", border_style="blue", expand=False))

    if not preserve_files:
        console.print("CAUTION! Preserving of files is OFF. Files will be deleted after merging.", style="underline bold red")

    if not typer.confirm("\nAre you certain you want to continue?"):
        if local_currentDirectory != outputFileFolder and outputFileFolder != "": # No need to delete a directory over '' which is the working directory
            try:
                print(f"Deleted temporary directory ({outputFileFolder})....")
                os.rmdir(outputFileFolder)
            except Exception as e:
                console.print(f"Error deleting temporary directory: {e}", style="red")
        raise typer.Abort()

    return True


def validateListForPDF(items, exclude, mimeCheck):
    """List Validation of eligible PDF files

    Args:
        items (list): Unchecked list of str as file path
        exclude (list) : List of excluded files that will remove from items
        mimeCheck (bool): Mimecheck of files using bool

    Raises:
        typer.BadParameter: Typer Exception if list has less than 2 PDF files

    Returns:
        list: Validated list of PDF files
    """

    valid_items = []
    for item in items:
        if not os.path.isdir(item) and os.path.exists(item) and getFileType(item) == "pdf" and item not in valid_items:
            valid_items.append(item)

    if mimeCheck:
        console.print("\nmimecheck enabled.\n", style="green")
        for item in valid_items:
            if magic.detect_from_filename(item).mime_type != "application/pdf":
                print(f"Caution! Automatic Ignore. {item} is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'")
                valid_items.remove(item)
    else:
        console.print("\nmimecheck not enabled. Fake PDF files cannot be detected. Use '-m' to enable. \n", style="dark_orange")

    valid_items = [i for i in valid_items if i not in exclude]

    # List needs to be more than 1 validated pdf to work with merge
    if len(valid_items) <= 1:
        raise typer.BadParameter(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return valid_items


def validateWorkingDirectory(target_file_path):
    """
    Validation of the folder path
    Checks if a folder path exists.
    If it doesn't, then create a folder for that path. Otherwise, the working script directory will be the saving folder path.
    If the folder path exists then the target folder path will be the saving folder path.

    Returns a validated folder path as str
    """
    trueFolderPath = getFileDirName(target_file_path)  # in case someone throws a directory of a file
    doesPathExist = os.path.isdir(trueFolderPath)

    if not doesPathExist:
        folder_creation_choice = typer.confirm(f"\nWarning! folder path {trueFolderPath} doesn't exist\nDo you wish to create it?")
        if folder_creation_choice:
            os.makedirs(trueFolderPath, exist_ok=True)
        else:
            print("\nCustom folder path creation aborted. Working directory will be the saving directory")
            trueFolderPath = os.getcwd()

    return trueFolderPath


def validateOverWrite(target_dir):
    """
    Prompts y/n as bool to get permission either to overwrite existing file or not
    """
    filename = getFileBaseName(target_dir)
    if os.path.exists(target_dir):
        return typer.confirm(f"\n{filename} already exists. Do you want to overwrite this file?")
    return False


def validateFileName(target_file_path):
    """
    Checks the filetype of the target directory filename.
    this will keep causing a prompt if the filetype doesn't match the correct type or the filename is SUS.
    """
    filename = getFileBaseName(target_file_path)
    folderpath = getFileDirName(target_file_path)
    while True:
        # if file is not a pdf format
        if getFileType(filename) != "pdf" or filename == "pdf":
            print(f"\nInvalid FileType name. Expected 'pdf'. Got {getFileType(filename)}")
            filename = typer.prompt("Enter saving filename: ")
            continue

        elif os.path.exists(returnStrPath(folderpath, filename)):
            # if the output already leads to an existing file and then user doesn't want to overwrite so they add another file
            #  and AGAIN make the same mistake like before, prompt them again!
            print(f"\nChanged file name ({filename}) already exists")
            if not validateOverWrite(returnStrPath(folderpath, filename)):
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break

    return getFileBaseName(filename)  # This function will return basename only. Path dir is not accepted.


def validateOutputFileName(target_file_path):
    """Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        validated_target_file_path (str): validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    # Otherwise, saving directory will say "" in confirmTask()
    folder_path = (
        os.getcwd() if getFileDirName(target_file_path) == ""
        else getFileDirName(target_file_path))
    final_filename = ""
    while True:
        final_filename = validateFileName(target_file_path)
        working_dir = validateWorkingDirectory(returnStrPath(folder_path, final_filename))

        break
    return returnStrPath(working_dir, final_filename)


def merge_runtime(input_file_list, outputFileName, preserve_files):
    """
    Takes 2 arguments, input_file_list and outputFileName
    This handles the main pdf merging.
    """

    try:
        doc = fitz.open()
        for file in input_file_list:
            doc.insert_file(file)
            # Remove files if preserve is removed
            if not preserve_files:
                os.remove(file)

        doc.save(outputFileName)
        console.print(Panel(f"""
File name: [i]{getFileBaseName(outputFileName)}[/i]
Folder: [i]{getFileDirName(outputFileName)}[/i]
""", title="MERGE COMPLETED", border_style="green", expand=False))

    except Exception as e:  # If output directory specified doesn't exist
        raise typer.BadParameter(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode. \nIt will ignore all files that are not PDF by mime.")


def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths. Tip: Pass '.' to include current directory.", rich_help_panel="Required")],
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging....", rich_help_panel="Additonal")]=[None],
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF file mime check. Files that failed the check will be removed from selection.", rich_help_panel="Options")]=True,
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    output: Annotated[str, typer.Option(help="Save output file name. Can Accept a folder directory as well.", rich_help_panel="Options")]="merged.pdf"):

    # In case the user passes "." as current working directory
    # List will include all files in the current working directory
    items.extend(os.listdir(os.getcwd()) if "." in items else items)

    accepted_file_list = validateListForPDF(items, exclude, mimecheck)
    validated_output_filename = ""

    if output == "--mimecheck":
        raise typer.BadParameter("--mimecheck mode can't be used with --output. Use --output to specify output file.")
    # if output is specified explicitly then it will trigger its validation process
    validated_output_filename = validateOutputFileName(output) if output != "merged.pdf" else "merged.pdf"

    if confirmTask(accepted_file_list, validated_output_filename, preserve):
        merge_runtime(accepted_file_list, validated_output_filename, preserve)
