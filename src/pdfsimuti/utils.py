import os
import importlib
from rich import print
from rich.table import Table

from click.exceptions import ClickException

### FIXED VARIBLES
workingDir = os.getcwd() # use this var on functions that calls os.getcwd() more than once
DEFAULT_SAVE_PDF_FILENAME = 'merged.pdf'
rejected_file_list = {}

### SHARED FUNCTIONS
class PrettyErrorDisplay(ClickException):
    """
    Raised when the program does something it wasn't supposed to.
     
    Imports from Click.exceptions.ClickException
    """


def has_pdf_extension(item) -> bool:
    """
    Returns the filetype by checking if it endswith .pdf
    Doesn't use name.endswith("pdf") because files like file/pdf returns True if used.
    Will return false if the item is just "pdf" and nothing else
    """
    return item.lower().split(".")[-1] == "pdf" and item != "pdf"


def get_full_path(folderpath:str, filename:str) -> str:
    """
    Returns absolute path of a file by combining folder path and file name

    Args:
        folderpath (str): folder name
        filename (str): file Name

    Returns:
        str: Full path of a file
    """
    return os.path.join(folderpath, filename)


def get_pdf_from_dir(directory: str) -> list:
    """
    Gets PDFs from a directory. 
    Only used in the validate_pdf_list when the user passes a directory address instead of the filename

    Args:
        directory (str): Directory path

    Returns:
        list: Pdf files from the list
    """

    directory = workingDir if "." in directory else directory
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = get_full_path(directory, folder_item)
        if has_pdf_extension(folder_path): pdf_files.append(folder_path)

    return pdf_files


def validate_fileList_via_mimecheck(fileList: list):
    """
    Mimecheck assisted updater to the rejected file lists.

    Args:
        fileList (list): PDF filepaths in a list
    """
    magic = importlib.import_module('magic')
    for item in fileList:
        file_mimecheck_result = magic.Magic(mime=True).from_file(item)
        if file_mimecheck_result != "application/pdf":
            rejected_file_list[item] = file_mimecheck_result
            

def validate_pdf_list(items, exclude, mimeCheck):
    """
    List Validation of eligible PDF files.
    Takes a list and removes incompatible item from the lists

    Args:
        items (list): Unchecked list of str as file path
        exclude (list) : List of excluded files that will remove from items
        mimeCheck (bool): Mimecheck of files using bool

    Raises:
        PrettyErrorDisplay: Typer Exception if list has less than 2 PDF files

    Returns:
        list: Validated list of PDF files
    """
    fileList = []
    
    for item in items:
        if item not in fileList and has_pdf_extension(item) and os.path.exists(item): fileList.append(os.path.abspath(item)) # ensures duplicates are not found.
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else item} [/yellow]")
            # Note: "." is actually an address to the current directory
            fileList.extend(get_pdf_from_dir(item))
        else: print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] {item} [/i]")

    # Performs mimechecking of the files from the list. Will update the list of any non-compatible files
    if mimeCheck:
        validate_fileList_via_mimecheck(fileList)
        display_rejected_files()
    else:
        print("\n[orange]Fake PDF files cannot be detected. Use '-m' to enable file mime checking")

    # [] is for NoneType to allow iteration of list
    fileList = list(dict.fromkeys([i for i in fileList or [] if i not in ((exclude and rejected_file_list) or [])]))
    

    # List needs to be more than 1 validated pdf to work with merge
    if len(fileList) <= 1: 
        raise PrettyErrorDisplay(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return fileList


def display_rejected_files() -> None:
    """
    Display the rejected files to the user in a table manner
    """
    if len(rejected_file_list) != 0:
        # display rejected files
        print(f"\n[yellow]CAUTION![/yellow] The following files have been ignored")
        table = Table(show_lines=True, highlight=True, expand=True)
        table.add_column("File No.", justify = "center", no_wrap=True)
        table.add_column("File Name", justify = "center", no_wrap=True)
        table.add_column("Received Type\n[i]Instead of 'application/PDF'[/i]", justify = "center", no_wrap=True)
        
        for index, (filename, filetype) in enumerate(rejected_file_list.items()): 
            table.add_row(str(index+1), filename, f'[red]{filetype}[/red]')
        
        print(table)