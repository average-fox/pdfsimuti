import os
import importlib
import struct # windows os + ghostScript only. Required to get CPU bit since gswin64c and gswin32c are different
import sys
from pathlib import Path

from rich import print

from click.exceptions import ClickException
import typer

CURRENT_DIR = os.getcwd()
DEFAULT_OUTPUT = 'merged.pdf'

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
        
        
def exit_program():
    print("[bold red]Program Exited[/bold red]")
    exit()
    

def return_confirm(msg:str='', caution:bool=False, default:bool=True) -> bool:
    """
    Prompt the user for a confirmation (Y/n) using Typer, defaulting to True on Enter.

    Args:
        msg (str): The confirmation message displayed to the user.
        caution (bool): Ask twice with extreme caution
        default (bool) : Default control behavior

    Returns:
        bool: True if confirmed (Y or Enter), False otherwise (n).
    """
    if caution:
        confirm_once = typer.confirm("Proceed to abort?", default=True)
        if not confirm_once:
            return typer.confirm("(final) Are you absolutely sure not to abort?", default=False)
        return False
    return typer.confirm(msg, default=default)


def get_calling_function():
    """
    Get the file basename of the function two stack frames up. This is required 
    by ``validate_pdf_list`` to specify return statement origins.

    Returns:
        str: The basename of the caller's Python file.
    """
    # thanks to https://stackoverflow.com/questions/3711184/how-to-use-inspect-to-get-the-callers-info-from-callee-in-python
    from inspect import getouterframes
    return return_basename(getouterframes(sys._getframe(1))[1].filename)


def rtn_gs_name() -> str:
    """
    Determine the correct Ghostscript executable name for cross-platform compatibility. 
    It checks the OS and architecture (gs, gswin64c, or gswin32c).

    Returns:
        str: The correct Ghostscript callname on the installed machine.
    """
    gs_name = "gs"
    
    # only linux and windows environments are supported. if there are others, well open an issue then :)
    # string appending is used here. its much less complicated.
    # intellsence will keep warning about this but its okay.
    if sys.platform == "win32":
        gs_name+="win"
        if 8*struct.calcsize("P"): gs_name+="64c"  
        else: gs_name+="32c"
        
    return gs_name
        

        
def return_basename(item: str) -> str:
    
    """
    Return the basename of a given filepath, regardless of the active directory.

    Args:
        item (str): The full or relative filepath.

    Returns:
        str: The final component of the path (the filename/basename).
    """
    return os.path.basename(item)


def return_dirname(item:str) -> str:
    """
    Return the directory path of a file, excluding the filename.

    Args:
        item (str): The full or relative filepath.

    Returns:
        str: The directory component of the path (the folder).
    """
    return os.path.dirname(item)


def return_abspath(item:str) -> str:
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


def scan_file(itemList: list) -> list:

    return_list = []
    for item in itemList:
        file = Path(item).resolve()
        # item can be either a file or a directory but not both
        if file.is_dir():
            for folder_item in file.glob("*.pdf"):
                folder_item = str(folder_item.resolve())
                if folder_item not in return_list: 
                    return_list.append(folder_item)
                else:
                    print(f"[yellow]CAUTION![/yellow] Duplicate file found and ignored: {folder_item}")
        # if dir but it doesn't exist
        else:
            if not file.is_file:
                print(f"[red]WARNING![/red] FOLDER not found: [i] [yellow]{str(file)}[/yellow] [/i]")
        
        # TODO: once has_pdf_extensions() is replaced with Pathlib, patch this up.
        if file.is_file() and not file.is_dir():
            if file.suffix.lower() == ".pdf":
                if str(file) not in return_list:
                    return_list.append(str(file))
                else:
                    print(f"[yellow]CAUTION![/yellow] Duplicate file found and ignored: {str(file)}")
            else:
                print(f"[red]WARNING![/red] File not PDF: {str(file)}")
        else:
            if not file.is_dir():
                print(f"[red]WARNING![/red] File not found: [i] [yellow]{str(file)}[/yellow] [/i]")

    return return_list



def update_file_dict_entry(item: tuple, mimecheck: bool) -> dict:
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
    file_validaty = None
    file_data = None

    # get size of files
    try: 
        file_data = os.path.getsize(filename)
    except Exception: file_data = "ERROR"

    # confirm magic exists
    try:
        magic = importlib.import_module('magic').Magic(mime=True) if mimecheck else None
    except ModuleNotFoundError:
        raise PrettyErrorDisplay("Package 'magic' required for mimecheck not found. Check your packages via [code]pdfsimuti checkhealth[/code]")

    # confirm fitz exists
    try:
        fitz = importlib.import_module('fitz')
    except ModuleNotFoundError:
        fitz = None
        print("[yellow]CAUTION![/yellow] PyMuPDF (fitz) not found. Skipping password protection check.")

    if not check_file_readability(filename):
        file_validaty = False
        file_data = "Unreadable file"
        
    elif magic and magic.from_file(filename) != "application/pdf":
        file_validaty = False
        file_data = f"Mimecheck pass failed.\nReceived:[yellow]\n{magic.from_file(filename)}[/yellow]"
    
    # TODO: either you fix this or change it with true try/except
    elif fitz:
        try:
            if fitz.open(filename).needs_pass:
                file_validaty = False
                file_data = 'Password Protected'
        except fitz.FileDataError:
            file_data = "Can't Open file"
    else:
        file_data = "Unknown.\nFitz not found."

    if file_validaty is None and mimecheck:
        file_validaty = True
    elif not mimecheck:
        file_validaty = None

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
    unvalidated_files = scan_file(items)
    excludeList = scan_file(exclude) if exclude else []
    filesDict = {item_entry: {"valid": None, "data": None} for item_entry in ([item for item in unvalidated_files if item not in excludeList] if exclude else unvalidated_files)}

    if not mimeCheck: print("[yellow]CAUTION![/yellow] Mimechecking disabled!")      

    # file that are existant are then scanned one by one
    for file_entry in filesDict.items():
        filesDict.update(update_file_dict_entry(file_entry, mimeCheck))

    # abort if no pdf files are found
    if len(filesDict) == 0:
        raise PrettyErrorDisplay(f"""
            No compatible PDF files found.
            \n[u]Search Locations[/u]: \n[i]{"\n".join(set([return_dirname(return_abspath(item)) for item in items]))}[/i]
        """)

    # in this stage, it counts the number of purely validated files after scanning for extensions, exclude and nature
    # this loop checks between true/false and none. if none then it's validation is unknown.
    final_validated_file_count = 0
    for item in filesDict.keys():
        valid = filesDict.get(item)['valid']
        if valid == None or valid == True: final_validated_file_count+=1

    match get_calling_function():
        case "compress.py": 
            return filesDict
        case "merge.py":
            if final_validated_file_count <= 1:
                print(return_validated_display(filesDict))
                raise PrettyErrorDisplay("Excepted at least 2 pdf files for merging.")
            return filesDict


def return_validated_display(filesDict:dict):
    """
    Returns the display output of files validated and rejected.
    
    Args:
        filesDict (dict): dict to validate the list from.

    Returns:
        str: validation outcome (rich-based)
    """
    from rich.table import Table
    index = 0
    validated_list_table = Table(show_lines=True)
    validated_list_table.add_column("SI", justify="center", vertical="middle")
    validated_list_table.add_column("Filename", vertical="middle")
    validated_list_table.add_column("Abspath", vertical="middle", overflow="fold")
    validated_list_table.add_column("Status", vertical="middle")
    validated_list_table.add_column("Size", vertical="middle", justify="center")

    for item in filesDict.keys(): 
        valid = filesDict.get(item)['valid']
        basename = os.path.splitext(return_basename(item))[0]
        data = filesDict.get(item)['data']
        size = str(data) if type(data) == int else "[red]X[/red]" # if the data is not a int then it is a str containing error. # TODO: pls optimize this
        if valid:
            validity = "[green]Verified[/green]" 
            index += 1
        elif valid == None:
            validity = "[yellow]Unknown[/yellow]"
            index += 1
        else:
            validity = filesDict.get(item)['data']
            item = f"[strike][red]{item}[/strike][/red]"
            basename = f"[strike][red]{basename}[/strike][/red]"

        # its a string conversion rather than type conversion.
        output = str(index) if valid == None or valid == True else "[red]X[/red]"
        validated_list_table.add_row(output, basename, item, validity, size)

    return validated_list_table
