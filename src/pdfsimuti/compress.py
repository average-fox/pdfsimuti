import typer
import magic
import fitz
import os

from typing_extensions import Annotated
from typing import List
from rich import print

app = typer.Typer()
workingDir = os.getcwd()


def hasPdfExtension(filename: str):
    """
    Returns the filetype by checking if it endswith .pdf
    """
    return filename.lower().split(".")[-1]


def getFileFullPath(folderpath, filename):
    """
    Returns absolute path of a file using os.path.join
    """
    return os.path.join(folderpath, filename)


def getPDFfromDirectory(directory):
    """
    Gets PDFs from a directory. Only used in the validateListForPDF when the user passes a directory address instead of the filename
    """
    directory = workingDir if "." in directory else directory
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = getFileFullPath(directory, folder_item)
        if hasPdfExtension(folder_path): pdf_files.append(folder_path)

    return pdf_files


def validateListForPDF(items: list, mimeCheck: bool, exclude: list = None):
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
    validFileItems = []
    for item in items:
        if item not in validFileItems and hasPdfExtension(item): 
            validFileItems.append(os.path.abspath(item))
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else item} [/yellow]")
            # Note: "." is actually an address to the current directory
            validFileItems.extend(getPDFfromDirectory(item))
        else: print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] {item} [/i]")

    # Sorts the list previously from set to remove duplicates and checks for exclude to remove. 
    # [] is for NoneType to allow iteration of list
    validFileItems = sorted(list(set([i for i in validFileItems or [] if i not in (exclude or [])])))

    if mimeCheck:
        print("\n[green]File mimechecking enabled.[/green]")
        for item in validFileItems:
            if magic.Magic(mime=True).from_file(item) != "application/pdf":
                print(f"[yellow]CAUTION! Automatic Merge Target Ignore. [bold red]{item}[/bold red] is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'[/yellow]")
                validFileItems.remove(item)
    else:
        print("\n[orange]mimecheck not enabled. Fake PDF files cannot be detected. Use '-m' to enable. \n[/orange]")

    # List needs to be more than 1 validated pdf to work with merge
    if len(validFileItems) <= 1:
        raise typer.BadParameter(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return validFileItems


def confirm(itemPDF) -> bool:
    pass


def compressPdf(itemList: list):
    for item in itemList:
        with fitz.open(item) as doc:
            # temp files created to solve incremental saving issue
            temp_file = item + ".temp"
            doc.save(temp_file, garbage=4, deflate=True)
        os.replace(temp_file, item)
        

def display_after_actions_report(): pass


def compress_runtime(itemList: list):
    compressPdf(itemList)


def compress(
        item: Annotated[List[str], typer.Argument(help="PDF files to be compressed")],
        mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
):
    valid_list = validateListForPDF(item, mimecheck)
    compress_runtime(valid_list)

