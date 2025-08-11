import os
import importlib
import struct # windows os + ghostScript only. Required to get CPU bit since gswin64c and gswin32c are different
import sys

from rich import print
from rich.text import Text
from rich.table import Table
from rich.panel import Panel

from click.exceptions import ClickException
import typer

rejected_file_list = {}
workingDir = os.getcwd()

DEFAULT_SAVE_PDF_FILENAME = 'merged.pdf'

### SHARED FUNCTIONS
class PrettyErrorDisplay(ClickException):
    """
    Raised when the program does something it wasn't supposed to.
     
    Imports from Click.exceptions.ClickException
    """
    
    def __init__(self, message):
        from rich.console import Console
        super().__init__(Console().render_str(message))
        
        
def return_confirm(msg:str) -> bool:
    return typer.confirm(msg, default=True); # default flag means enter key = y


def return_ghostscript_callname() -> str:
    """
    Returns the ghostscript callname. 
    Could be either gs, gswin64c or gswin32c

    Returns:
        str: ghostscript callname
    """
    gs_name = "gs"
    
    # only linux and windows environments are supported. if there are others, well open an issue then :)
    # string appending is used here. its much less complicated.
    if sys.platform == "win32":
        gs_name+="win"
        if 8*struct.calcsize("P"): gs_name+="64c"  
        else: gs_name+="32c"
        
    return gs_name
        

        
def return_filepath_basename(item: str) -> str:
    """
    Returns the basename of a filepath.
    Created if the user sends a path outside of the active directory

    Args:
        item (str): filepath 

    Returns:
        str: basename of the filepath
    """
    return os.path.basename(item)


def return_filepath_dirname(item:str) -> str:
    """
    Returns the directory folder path of the file

    Args:
        item (str): filepath

    Returns:
        str: folder of the filepath
    """
    return os.path.dirname(item)


def return_absolute_filePath(item:str) -> str:
    """
    Returns the absolute filepath of an existant file.

    Args:
        item (str): name of the file

    Returns:
        str: absolute path of the file
    """
    return os.path.abspath(item)


def has_pdf_extension(item) -> bool:
    """
    Returns the filetype by checking if it endswith .pdf
    Doesn't use name.endswith("pdf") because files like file/pdf returns True if used.
    Will return false if the item is just "pdf" and nothing else
    """
    return item.lower().split(".")[-1] == "pdf" and item != "pdf"


def return_joined_filePath(folderpath:str, filename:str) -> str:
    """
    Returns absolute path of a file by joining folder path and file name.
    This function is reserved for path that aren't real/exists.

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
        folder_path = return_joined_filePath(directory, folder_item)
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
    Takes a list and removes incompatible item from the lists.
    Scans a directory to determine either it's real or fake.

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
    
    # start everything from new line
    print()
    
    for item in items:
        if item not in fileList and has_pdf_extension(item) and os.path.exists(item): 
            fileList.append(return_absolute_filePath(item)) # ensures duplicates are not found.
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else f"[i]{return_absolute_filePath(item)}[/i]"} [/yellow]")
            # Note: "." is actually an address to the current directory
            fileList.extend(get_pdf_from_dir(item))
        else: 
            print(f"[white on red]WARNING![/white on red] FOLDER/ITEM not found: [i] [yellow]{return_absolute_filePath(item)}[/yellow] [/i]")
        
    if len(set(fileList)) != len(fileList): 
        print("\n[yellow]CAUTION![/yellow] Duplicates found and got ignored.")

    # Performs mimechecking of the files from the list. Will update the list of any non-compatible files
    if mimeCheck:
        validate_fileList_via_mimecheck(fileList)
        display_rejected_files()
    else:
        print("\n[orange]Fake PDF files cannot be detected. Use '-m' to enable file mime checking")

    # [] is for NoneType to allow iteration of list
    excludeList = [return_absolute_filePath(excludeItem) for excludeItem in exclude if excludeItem != None]
    fileList = list(dict.fromkeys([item for item in fileList or [] if (item not in rejected_file_list or []) and (item not in excludeList)]))
    

    # List needs to be more than 1 validated pdf to work with merge
    if len(fileList) <= 1: 
        raise PrettyErrorDisplay(
            f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.\n\n"
            f"[u]Search Locations[/u]: \n[i]{"\n".join(set([return_absolute_filePath(item) for item in items]))}[/i]")

    return fileList


def display_rejected_files() -> None:
    """
    Display the rejected files to the user in a table manner
    """
    if len(rejected_file_list) != 0:
        # display rejected files
        print(f"\n[yellow]CAUTION![/yellow] The following files have been rejected due to mimecheck.")
        table = Table(show_lines=True, highlight=True)
        table.add_column("File No.", justify = "center", no_wrap=True)
        table.add_column("File Name", justify = "center", no_wrap=True)
        table.add_column("File Path (Absolute)", justify = "center", no_wrap=True)
        table.add_column("Received Type\n[i]Instead of 'application/PDF'[/i]", justify = "center", no_wrap=True)
        
        for index, (filename, filetype) in enumerate(rejected_file_list.items()): 
            table.add_row(str(index+1), os.path.basename(filename), os.path.abspath(filename), f'[red]{filetype}[/red]')
        
        print(Panel(table, subtitle="[red]Rejected files[/red]", expand=False))