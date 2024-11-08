import typer
import fitz # fitz is actually PyMuPDF
import magic
import os
from typing import List # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated


app = typer.Typer()



def getFileType(filename):
    """
    Returns the filetype by checking if it endswith .pdf
    """
    return filename.lower().split('.')[-1]


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
    outputFileFolder = getFileDirName(outputFileName)
    # Calculate estimated size of the merge
    fileSize = 0
    for i in itemsList:
        fileSize+=(os.path.getsize(i) / (1024*1024))

    print(f"""
The following files will be merged: {itemsList}
Output file is: {getFileBaseName(outputFileName)}
Saving directory is: {outputFileFolder}
Estimated Size: More than{fileSize: .2f} MB
    """)

    if not preserve_files:
        print("Caution! Preserving of files is off. Files will be deleted after merging")

    choice = typer.confirm("\nAre you certain you want to continue?")
    if not choice:
        # if user created the custom saving directory, delete the newly created directory.
        # It assumes that the saving directory is not the working directory.
        # Directories can be created from validateOutputFileName()
        try:
            if os.getcwd() != outputFileFolder and outputFileFolder != "": # No need to delete a directory over '' which is the working directory
                print(f"Cleaning created directory ({outputFileFolder})....")
                os.rmdir(outputFileFolder)
        except Exception as e:
            print(e)
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

    valid_items=[]
    for item in items:
        # Include item in valid list if
        # 1. It exists on the system via os.path.exists(item)
        # 3. It has a filetype of "pdf"
        # 2. It is not already a directory of some folders
        # 4. It is not already included in items as duplicate
        if not os.path.isdir(item) and os.path.exists(item) and getFileType(item) == "pdf" and item not in valid_items:
            valid_items.append(item)

    if mimeCheck:
        print("\nmimecheck is enabled.\n")
        for item in valid_items:
            if magic.detect_from_filename(item).mime_type != "application/pdf":
                print(f"Caution! Automatic Ignore. {item} is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'")
                valid_items.remove(item)

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
    trueFolderPath = getFileDirName(target_file_path) # in case someone throws a directory of a file
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
        # WARNING: If filename is only 'pdf' then it will pass the checks. That is not accepted. Solution: Advanced search using mimetypes
        if getFileType(filename) != "pdf":
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

    return getFileBaseName(filename) # This function will return basename only. Path dir is not accepted.


def validateOutputFileName(target_file_path):
    """Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        validated_target_file_path (str): validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    # Otherwise, saving directory will say "" in confirmTask()
    folder_path = os.getcwd() if getFileDirName(target_file_path) == "" else getFileDirName(target_file_path)
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
        print(f"File Saved as {getFileBaseName(outputFileName)} over {getFileDirName(outputFileName)}")

    except Exception as e: # If output directory specified doesn't exist
        raise typer.BadParameter(f"Error. {e}. \nRecommended to run `pdfsimuti merge` with --mimecheck mode. \nIt will ignore all files that are not PDF by mime.")


@app.command(help="Merges [italic]n[/italic] number of PDFs into a super PDF.")
def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge. Can accept file paths. Tip: Pass '.' to include current directory.")],
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging....")]=None,
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF file mime check. Files that failed the check will be removed from selection.")]=False,
    preserve: Annotated[bool, typer.Option(help="Preserve the files after merging..")] = True,
    output: Annotated[str, typer.Option(help="Save output file name. Can Accept a folder directory as well.")]="merged.pdf"):

    # In case the user passes "." as current working directory
    # List will include all files in the current working directory
    for item in items:
        if item == ".":
            items.extend(os.listdir(os.getcwd())) # Adds two lists into 1

    accepted_file_list = validateListForPDF(items, exclude, mimecheck)
    validated_output_filename = ""

    # If normal output is not "merged.pdf" then perform extensive validation checks
    if output != "merged.pdf":
        validated_output_filename = validateOutputFileName(output)

    # In case that the user passes --mimecheck after --output and not adding anything
    # For example: pdfsimuti merge . --output --mimecheck
    elif output == "--mimecheck":
        raise typer.BadParameter("--output takes no option. What are you doing?")
    else:
        validated_output_filename = "merged.pdf"

    if confirmTask(accepted_file_list, validated_output_filename, preserve):
        merge_runtime(accepted_file_list, validated_output_filename, preserve)
