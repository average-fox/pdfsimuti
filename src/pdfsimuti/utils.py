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
    Remove common leading whitespace and strip surrounding space/newlines.

    Args:
        msg (str): The multi-line string content to dedent.

    Returns:
        (str): The dedented string with no leading or trailing whitespace.
    """
    import textwrap
    return textwrap.dedent(msg).strip()


class PrettyErrorDisplay(ClickException):
    """
    Imports from Click.exceptions.ClickException to create a pretty error display.
    """
    
    def __init__(self, message):
        from rich.console import Console
        super().__init__(Console().render_str(text_dedent(message)))
        
        
def return_confirm(msg:str, default:bool=True) -> bool:
    """
    Prompt the user for a confirmation (Y/n) using Typer, defaulting to True on Enter.

    Args:
        msg (str): The confirmation message displayed to the user.
        default (bool) : Default control behavior

    Returns:
        bool: True if confirmed (Y or Enter), False otherwise (n).
    """
    return typer.confirm(msg, default=default); # default flag means enter key = y


def get_calling_function():
    """
    Get the file basename of the function two stack frames up. This is required 
    by ``validate_pdf_list`` to specify return statement origins.

    Returns:
        str: The basename of the caller's Python file.
    """
    from inspect import currentframe
    
    return return_filepath_basename(currentframe().f_back.f_back.f_code.co_filename)


def return_ghostscript_callname() -> str:
    """
    Determine the correct Ghostscript executable name for cross-platform compatibility. 
    It checks the OS and architecture (gs, gswin64c, or gswin32c).

    Returns:
        str: The correct Ghostscript callname on the installed machine.
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
    Return the basename of a given filepath, regardless of the active directory.

    Args:
        item (str): The full or relative filepath.

    Returns:
        str: The final component of the path (the filename/basename).
    """
    return os.path.basename(item)


def return_filepath_dirname(item:str) -> str:
    """
    Return the directory path of a file, excluding the filename.

    Args:
        item (str): The full or relative filepath.

    Returns:
        str: The directory component of the path (the folder).
    """
    return os.path.dirname(item)


def return_absolute_path(item:str) -> str:
    """
    Return the normalized absolute path of a file or directory.

    Args:
        item (str): The relative or absolute path of the file.

    Returns:
        str: The absolute path of the file.
    """
    return os.path.abspath(item)


def check_file_readability(item: str) -> bool:
    """
    Check if a file can be opened and read by attempting to open it.

    Args:
        item (str): The path to the file to check.

    Returns:
        bool: True if the file is readable (no exception), False otherwise.
    """
    return os.path.isfile(item) and os.access(item, os.R_OK)


def has_pdf_extension(filename: str) -> bool:
    """
    Check if a file or path has the '.pdf' extension, ignoring case. 
    It specifically prevents false positives like "file/pdf" and excludes the string "pdf".

    Args: 
        filename (str): The filename or filepath to check.

    Returns:
        bool: True if the filename has a valid '.pdf' extension, False otherwise.
    """
    return filename.lower().split(".")[-1] == "pdf" and filename != "pdf"


def return_joined_filePath(folderpath:str, filename:str) -> str:
    """
    Construct a full file path by safely joining a folder path and a filename. 
    This is primarily used for generating paths that may not yet exist on the filesystem.

    Args:
        folderpath (str): The directory or folder name.
        filename (str): The file name.

    Returns:
        str: The full, combined path string.
    """
    return os.path.join(folderpath, filename)


def scan_dir_files(filesDict: dict, directory: str) -> dict:
    """
    Scan a specified directory, identify files with a '.pdf' extension, and add them to a dictionary for validation. 
    Duplicate files encountered are noted and ignored.

    Args:
        filesDict (dict): The dictionary used to store file paths and their validation status.
        directory (str): The path to the directory to scan for PDF files.

    Returns:
        filesDict (dist): The updated ``filesDict`` containing all unique PDF file paths found in the directory.

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


def update_file_dict_entry(item: tuple, mimecheck: bool):
    """
    Validate a single file dictionary entry by performing readability, MIME type, and password checks. 
    It updates the 'valid' and 'data' fields based on the outcome of these checks.

    Args:
        item (tuple): A tuple containing the file path and its current dictionary entry
        mimecheck (bool): Flag to indicate if the external 'magic' library should be used for MIME type validation.

    Returns:
        dict: The updated dictionary entry for the file ``{filename: {"valid": bool, "data": Any}}``
    """
    filename = item[0]
    file_validaty = item[1]['valid']
    file_data = item[1]['data']

    try:
        magic = importlib.import_module('magic').Magic(mime=True) if mimecheck else None
    except ModuleNotFoundError:
        raise PrettyErrorDisplay("Package 'magic' required for mimecheck not found. Check your packages via [code]pdfsimuti checkhealth[/code]")
        
    if not check_file_readability(filename):
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


def validate_pdf_dict(items, exclude, mimeCheck):
    """
    Perform multi-step validation and cleanup of a list of file and directory paths for eligible PDF files. 
    It handles directory and extension scanning before passing it to `update_file_dict_entry()` for validation.

    Args:
        items (list): An unchecked list of file or directory paths.
        exclude (list): A list of file paths to explicitly exclude from the final results.
        mimeCheck (bool): Boolean flag to enable/disable external MIME type validation using the 'magic' package.

    Raises:
        PrettyErrorDisplay: If no compatible PDF files are found, or if the calling script 
            (e.g., 'merge.py') requires a minimum number of files that isn't met.

    Returns:
        dict: A validated dictionary of PDF file paths ready for processing.
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
        else:
            filesDict[item] = {"valid": None, "data": None}
    
    for file_entry in filesDict.items():
        if file_entry[0] not in exclude:
            filesDict.update(update_file_dict_entry(file_entry, mimeCheck))
    
    if exclude: filesDict = {key:value for key,value in filesDict.items() if key not in excludeList}
            
    # TODO: Remove this. it won't be required after doing the BOX-IN design
    rejected_files_dict = {key:value['data'] for key, value in filesDict.items() if value['valid'] == False}
    if len(rejected_files_dict) > 0:
        display_rejected_files(rejected_files_dict)
        filesDict = {key:value for key, value in filesDict.items() if value['valid'] == True}
    
    if len(filesDict) == 0:
        raise PrettyErrorDisplay(f"""
            No compatible PDF files found.
            \n[u]Search Locations[/u]: \n[i]{"\n".join(set([return_filepath_dirname(return_absolute_path(item)) for item in items]))}[/i]
        """)

    match get_calling_function():
        case "compress.py": 
            return filesDict
        case "merge.py":
            if len(filesDict) <= 1:
                raise PrettyErrorDisplay("Excepted at least 2 pdf files for merging.")
            return filesDict


def display_rejected_files(rejected_files_dict: dict) -> None:
    """
    Generate and display a formatted table listing all files that were rejected during validation.

    Args:
        rejected_files_dict (dict): A dictionary of rejected file paths and their corresponding rejection causes.
    """
    print(f"\n[yellow]CAUTION![/yellow] The following file(s) have been rejected.")
    table = Table(show_lines=True, highlight=True)
    table.add_column("File No.", justify = "center", no_wrap=True)
    table.add_column("File Name", justify = "center", no_wrap=True)
    table.add_column("File Path (Absolute)", justify = "center", no_wrap=True)
    table.add_column("Cause", justify = "center", no_wrap=True)
    
    for index, (file, error_type) in enumerate(rejected_files_dict.items()): 
        table.add_row(str(index+1), os.path.basename(file), os.path.abspath(file), f'[red]{error_type}[/red]')
    
    print(Panel(table, subtitle="[red]Rejected files[/red]", expand=False))


def return_rich_validated_display_block(filesDict:dict):
    validated_list_table = Table(show_lines=True)
    validated_list_table.add_column("Index")
    validated_list_table.add_column("Filename")
    validated_list_table.add_column("Absolute Path")
    for index, item in enumerate(filesDict):
        validated_list_table.add_row(str(index+1), return_filepath_basename(item), item)

    
    return validated_list_table
