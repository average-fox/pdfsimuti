import os
import importlib
import struct # windows os + ghostScript only. Required to get CPU bit since gswin64c and gswin32c are different
import sys

from rich import print
from rich.table import Table
from rich.panel import Panel

from click.exceptions import ClickException
import typer

workingDir = os.getcwd()
DEFAULT_SAVE_PDF_FILENAME = 'merged.pdf'

def text_dedent(msg : str) -> str:
    """
    Detents a triple quote print statement using textwrap

    Args:
        msg (str): String to dedent

    Returns:
        str: Detended string
    """
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
    """
    Typer based confirm y/n.
    Default is y.
    
    Args:
        msg (str): Typer confirm message.

    Returns:
        bool: Outcome of confirm
    """
    return typer.confirm(msg, default=True); # default flag means enter key = y


def get_calling_function():
    """
    Returns the file basename that called this python file.

    Returns:
        str: caller filename
    """
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
    
    Args: 
        item (str): filename or filepath
    Returns:
        bool: outcome
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


def scan_dir_files(filesDict: list, directory: str) -> list:
    """
    Scans a given directory for PDF files and returns validated files in a list
    Args:
        filesDict (dict) : file dict to be appended
        directory (str) : directory path for PDF file scanning
    Returns:
        filesDict (dict) : updated filesDict with included directory files
    """
    directory = workingDir if directory == "." else return_absolute_path(directory)
    print(f"ADDDING FOLDER: [yellow]{"CURRENT DIRECTORY" if directory == workingDir else directory} [/yellow]")
    
    for item in os.listdir(directory):
        folder_path = return_joined_filePath(directory, item)
        if has_pdf_extension(folder_path):
            if folder_path not in filesDict: 
                filesDict[folder_path] = {"valid": None, "data": None}
            else:
                print(f"[yellow]CAUTION[/yellow]! Duplicate file found and ignored: {folder_path}")    

    return filesDict


def update_file_dict_entry(item: tuple, mimecheck):
    """
    Mimecheck assisted updater to filesList.

    Args:
        filesDict (dict): PDF filepaths in a dict
    """
    filename = item[0]
    file_validaty = item[1]['valid']
    file_data = item[1]['data']

    try:
        magic = importlib.import_module('magic').Magic(mime=True) if mimecheck else None
    except ModuleNotFoundError:
        raise PrettyErrorDisplay("Package 'magic' required for mimecheck not found. Check your packages via [code]pdfsimuti checkhealth[/code]")
        
    if not check_if_openable(filename):
        file_validaty = False
        file_data = "Unreadable file"
        
    elif magic and magic.from_file(filename) != "application/pdf":
        file_validaty = False
        file_data = f"Mimecheck pass fail \nReceived: {magic.from_file(filename)}"
        
    elif importlib.util.find_spec('fitz') is not None:
        if importlib.import_module('fitz').open(filename).needs_pass:
            file_validaty = False
            file_data = "Password Protected"
    else:
        print("[yellow]CAUTION![/yellow] Package 'PyMuPDF' not found. Skipping password protection check.")
    
    if file_validaty is None:
        file_validaty = True
        file_data = os.path.getsize(filename)
   
    return {filename: {"valid": file_validaty, "data": file_data}}


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
        PrettyErrorDisplay: Typer Exception if list has less than 2 PDF files for merge.py

        
    """

    excludeList = [return_absolute_path(excludeItem) for excludeItem in exclude if excludeItem != None]
    filesDict = {}
    
    # start everything from new line
    print()
    
    # this loop will not scan the items. They will only be added to be scanned on the second loop
    for item in items:
        item = return_absolute_path(item)
        if os.path.isdir(item):
            # if item in excludeList, skip the scan
            if item in excludeList:
                pass
            filesDict = scan_dir_files(filesDict, item)
        elif not os.path.exists(item):
            print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] [yellow]{return_absolute_path(item)}[/yellow] [/i]")
        elif not has_pdf_extension(item):
            print("[yellow]CAUTION![/yellow] Target file not PDF. Extension mismatch.")    
        elif item in filesDict:
            print(f"[yellow]CAUTION![/yellow] Duplicate file found and ignored: {item}")
        # TODO: expand this code. run the validations as entries here!!
        # BUG: the files added via the scan_dirs_files aren't validated !!
        # BUG: PLEASE FIX THIS SHIT. ITS ALL FUBAR!!
        else:
            filesDict[item] = {"valid": None, "data": None}
    
    
    for file_entry in filesDict.items():
        if file_entry[0] not in exclude:
            filesDict.update(update_file_dict_entry(file_entry, mimeCheck))
    
    if exclude:
        filesDict = {key:value for key,value in filesDict.items() if key not in excludeList}
    
    # display rejected files. If it exists
    rejected_files_dict = {key:value['data'] for key, value in filesDict.items() if value['valid'] == False}
    
    if len(rejected_files_dict) > 0:
        display_rejected_files(rejected_files_dict)
        filesDict = {key:value for key, value in filesDict.items() if value['valid'] == True}
    
    if len(filesDict) == 0:
        raise PrettyErrorDisplay(f"""
            No compatible PDF files found.
            \n[u]Search Locations[/u]: \n[i]{"\n".join(set([return_filepath_dirname(return_absolute_path(item)) for item in items]))}[/i]
        """)
    
    
    fileList = list(filesDict.keys())
    match get_calling_function():
        case "compress.py": 
            return fileList
        case "merge.py":
            if len(fileList) <= 1:
                raise PrettyErrorDisplay("Excepted at least 2 pdf files for merging.")
            return fileList


def display_rejected_files(rejected_files_dict: dict) -> None:
    """
    Display the rejected files to the user in a table manner
    
    Args:
        filesDict(dict): filesDict with valid and data keys
    """
    # display rejected files
    print(f"\n[yellow]CAUTION![/yellow] The following file(s) have been rejected.")
    table = Table(show_lines=True, highlight=True)
    table.add_column("File No.", justify = "center", no_wrap=True)
    table.add_column("File Name", justify = "center", no_wrap=True)
    table.add_column("File Path (Absolute)", justify = "center", no_wrap=True)
    table.add_column("Cause", justify = "center", no_wrap=True)
    
    for index, (file, error_type) in enumerate(rejected_files_dict.items()): 
        table.add_row(str(index+1), os.path.basename(file), os.path.abspath(file), f'[red]{error_type}[/red]')
    
    print(Panel(table, subtitle="[red]Rejected files[/red]", expand=False))