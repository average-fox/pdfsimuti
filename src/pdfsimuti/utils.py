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


def text_dedent(msg : str):
    import textwrap
    return textwrap.dedent(msg).strip()


### SHARED FUNCTIONS
class PrettyErrorDisplay(ClickException):
    """
    Raised when the program does something it wasn't supposed to.
     
    Imports from Click.exceptions.ClickException
    """
    
    def __init__(self, message):
        from rich.console import Console
        super().__init__(Console().render_str(text_dedent(message)))
        
        
def return_confirm(msg:str) -> bool:
    return typer.confirm(msg, default=True); # default flag means enter key = y


def get_calling_function():
    from inspect import currentframe
    
    return return_filepath_basename(currentframe().f_back.f_back.f_code.co_filename)



def return_ghostscript_callname() -> str:
    """
    Returns the ghostscript callname. 
    Could be either gs, gswin64c or gswin32c

    Returns:
        str: actual ghostscript callname on the installed machine
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


def return_absolute_path(item:str) -> str:
    """
    returns the abspath. works as os.path.abspath(ITEM)

    Args:
        item (str): name of the file

    Returns:
        str: absolute path of the file
    """
    return os.path.abspath(item)


def check_if_openable(item: str) -> bool:
    """
    Determines if a PDF can be opened or not. Returns depending on weither it got an exception or not

    Args:
        item (str): PDF file

    Returns:
        bool: outcome
    """
    try:
        with open(item, "r") as doc:
            return True
    except Exception:
        return False
    


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


def return_pdfFiles_fromDir(directory: str) -> list:
    """
    Gets PDFs from a directory. 
    Only used in the validate_pdf_list when the user passes a directory address instead of the filename

    Args:
        directory (str): Directory path

    Returns:
        list: PDF absolute filepaths from the directory
    """
    # Note: "." is actually an address to the current directory
    directory = workingDir if directory == "." else return_absolute_path(directory)
    print(f"ADDDING FOLDER: [yellow]{"CURRENT DIRECTORY" if directory == workingDir else directory} [/yellow]")
            
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = return_joined_filePath(directory, folder_item)
        if has_pdf_extension(folder_path): pdf_files.append(folder_path)
    return pdf_files


def validate_fileList_write_capability(fileList: list, mimecheck):
    """
    Mimecheck assisted updater to the rejected file lists.

    Args:
        fileList (list): PDF filepaths in a list
    """
    try:
        magic = importlib.import_module('magic').Magic(mime=True) if mimecheck else None
    except ModuleNotFoundError:
        raise PrettyErrorDisplay("Package 'magic' required for mimecheck not found. Check your packages via [code]pdfsimuti checkhealth[/code]")
        
    for item in fileList:
        if not check_if_openable(item):
            rejected_file_list[item] = "[red]No Write Permission[/red]"
            continue
        elif magic and magic.from_file(item) != "application/pdf":
            rejected_file_list[item] = f"[red]Mimecheck pass fail[/red] \nReceived: {magic.from_file(item)}"
            continue

        if importlib.util.find_spec('fitz') is not None and importlib.import_module('fitz').open(item).needs_pass:
            rejected_file_list[item] = "[red]Password Protected[/red]"



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

    Returns (if match case):
        list: Validated list of PDF files
        
    """
    fileList = []
    
    # start everything from new line
    print()
    
    for item in items:
        # updates the list of files that are present or not
        if item not in fileList and has_pdf_extension(item) and os.path.exists(item):
            fileList.append(return_absolute_path(item)) # ensures duplicates are not found.
        elif os.path.isdir(item):
            fileList.extend(return_pdfFiles_fromDir(item))
        else: 
            print(f"[white on red]WARNING![/white on red] FOLDER/ITEM not found: [i] [yellow]{return_absolute_path(item)}[/yellow] [/i]")  
        
    if len(set(fileList)) != len(fileList): 
        print("\n[yellow]CAUTION![/yellow] Duplicates found and got ignored.")

    # Performs write permissions of the files from the list. Will update the fileList of any non-compatible files
    validate_fileList_write_capability(fileList, mimeCheck)

    # [] is for NoneType to allow iteration of list
    excludeList = [return_absolute_path(excludeItem) for excludeItem in exclude if excludeItem != None]
    fileList = list(dict.fromkeys([item for item in fileList or [] if (item not in rejected_file_list or []) and (item not in excludeList)]))
    
    # display rejected files. If it exists
    if len(rejected_file_list) != 0: display_rejected_files()
    
    if len(fileList) == 0:
        raise PrettyErrorDisplay(f"""
            No compatible PDF files found.
            \n[u]Search Locations[/u]: \n[i]{"\n".join(set([return_absolute_path(item) for item in items]))}[/i]
        """)
    
    
    match get_calling_function():
        case "compress.py": 
            return fileList
        case "merge.py":
            if len(fileList) <= 1:
                raise PrettyErrorDisplay("Excepted more than 1 compatible PDF file for merging.")


def display_rejected_files() -> None:
    """
    Display the rejected files to the user in a table manner
    """

    # display rejected files
    print(f"\n[yellow]CAUTION![/yellow] The following file(s) have been rejected.")
    table = Table(show_lines=True, highlight=True)
    table.add_column("File No.", justify = "center", no_wrap=True)
    table.add_column("File Name", justify = "center", no_wrap=True)
    table.add_column("File Path (Absolute)", justify = "center", no_wrap=True)
    table.add_column("Cause", justify = "center", no_wrap=True)
    
    for index, (filename, filetype) in enumerate(rejected_file_list.items()): 
        table.add_row(str(index+1), os.path.basename(filename), os.path.abspath(filename), f'{filetype}')
    
    print(Panel(table, subtitle="[red]Rejected files[/red]", expand=False))