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

def text_dedent(msg) -> str:
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
        from io import StringIO
        console = Console(file=StringIO(), force_terminal=True)
        with console.capture() as capture: console.print(text_dedent(message))
        
        super().__init__(capture.get())
        

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
        confirm_once = typer.confirm("Proceed", default=False)
        if confirm_once:
            return typer.confirm("Are you sure to proceed?", default=False)
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


def return_joined_filePath(filePath1:str, filePath2:str) -> str:
    return os.path.join(filePath1, filePath2)


def txt_file_reader(victimFile, filePath:str) -> list:

    if not filePath.endswith(".txt"): 
        print(f"[yellow]Caution[/yellow]--source file:{filePath} is not a .txt file in suffix")
        return victimFile

    print('Reading text file....')

    try:
        with open(filePath, 'r') as file:
            victimFile.extend(line.strip() for line in file)
    except FileNotFoundError:
        raise PrettyErrorDisplay(f"--source file not found: [purple]{filePath}[/purple]")
    except Exception as e:
        raise PrettyErrorDisplay(f"Error with the source file.\nError: {e}")
    
    return victimFile


def scan_items_entry(itemList: list) -> list:

    return_list = []
    for item in itemList:
        file = Path(item).resolve()
        file_type = "directory" if file.is_dir() else "file" if file.is_file() else "unknown"
        file_suffix = file.suffix.lower()

        # case 1:it's a directory
        if file_type == "directory":
            # look for pdf in the directory
            for folder_item in file.glob("*.pdf"):
                folder_item = str(folder_item.resolve())
                # duplicate guard
                if folder_item not in return_list:
                    return_list.append(folder_item)
                else:
                    print(f"[yellow]CAUTION![/yellow] Duplicate file found and ignored: {folder_item}")

        # case 2: its a file
        elif file_type == "file":
            if file_suffix == ".pdf":
                if str(file) not in return_list:
                    return_list.append(str(file))
                else:
                    print(f"[yellow]CAUTION![/yellow] Duplicate file found and ignored: [i][yellow]{str(file)}[/yellow] [/i]")
            else:
                print(f"[red]WARNING![/red] File not PDF: [i][yellow]{str(file)}[/yellow] [/i]")
        
        # case 3: its neither and looks like a directory
        elif file_suffix == "" and file_type == "unknown":
            print(f"[red]WARNING![/red] Folder not found: [i][yellow]{str(file)}[/yellow] [/i]")
        
        else:
            print(f"[red]WARNING![/red] File not found: [i][yellow]{str(file)}[/yellow] [/i]")

    return return_list


def return_validate_pdf_dict(filesDict: dict, mimecheck: bool):
    
    # 1. verify fitz 
    try:
        fitz = importlib.import_module('fitz')
    except ModuleNotFoundError:
        fitz = None
        print("[yellow]CAUTION![/yellow] PyMuPDF (fitz) not found. Skipping password protection check.")

    # 2. confirm magic exists. 
    # if it doesnt and user still approves it; raise error
    try:
        magic = importlib.import_module('magic').Magic(mime=True) if mimecheck else None
    except ModuleNotFoundError:
        raise PrettyErrorDisplay("Package 'magic' required for mimecheck not found. Check your packages via [code]pdfsimuti checkhealth[/code]")

    # 3. start validation loop over dict
    for file_items in filesDict.items():
        file_name = file_items[0]
        file_mime = magic.from_file(file_items[0]) if magic else None
        # 3.1. get size of the file
        try:
            file_items[1]['initial_size'] = Path(file_name).stat().st_size
        except Exception:
            file_items[1]['valid'] = False
            file_items[1]['state'] = 'ERROR'

        # 3.2. check file readability
        if not check_file_readability(file_items[0]):
            file_items[1]['valid'] = False
            file_items[1]['state'] = "Unreadable file"

        # 3.3. check file mime
        elif magic and file_mime != "application/pdf":
            file_items[1]['valid'] = False
            file_items[1]['state'] = f"Mimecheck pass failed.\nReceived:[yellow]\n{file_mime}[/yellow]"

        # 3.4. check password protection (uses fitz)
        elif fitz:
            try:
                if fitz.open(file_items[0]).needs_pass:
                    file_items[1]['valid'] = False
                    file_items[1]['state'] = 'Password Protected'
            except fitz.FileDataError:
                file_items[1]['state'] = "Can't Open file."
        
        # 3.5 state file validity. if none; that meant mimecheck is disabled.
        if file_items[1]['valid'] is None and mimecheck:
            file_items[1]['valid'] = True
        elif file_items[1]['initial_size'] == 0:
            file_items[1]['valid'] = False
            file_items[1]['state'] = "[red]File is empty[/red]"
        elif not mimecheck:
            file_items[1]['valid'] = None

    return filesDict

            
def validate_pdf_dict(items, source, exclude, excludeSource, mimecheck):

    items = items or [] # without this, item will be treated as NoneType
    items = txt_file_reader(items, source) if source else items
    exclude= txt_file_reader(exclude, excludeSource) if excludeSource else exclude
    
    unvalidated_files = scan_items_entry(items)
    excludeList = scan_items_entry(exclude) if exclude else []

    if not mimecheck: print("[yellow]CAUTION![/yellow] Mimechecking disabled! Corrupted files can disrupt the process.")  

    # template for file dict
    newFilesDict = {item_entry: {'saving_path': item_entry, 'valid': None, 'state': None, 'initial_size': 0, 'final_size': 0} for item_entry in ([filePaths for filePaths in unvalidated_files if filePaths not in excludeList] if exclude else unvalidated_files)} 
    validatedFilesDict = return_validate_pdf_dict(newFilesDict, mimecheck)

    # in this stage, it counts the number of purely validated files after scanning for extensions, exclude and type of the file (mimecheck)
    # this loop checks between true/false and none. if none then it's validation is unknown.
    final_validated_file_count = 0
    for item in validatedFilesDict.items():
        valid = item[1]['valid']
        if valid == None or valid == True: final_validated_file_count+=1

    # this works not only for merge but also for compress. If no valid files are found, it shouldn't proceeed.
    if final_validated_file_count == 0:
        raise PrettyErrorDisplay("No compatible PDF files found.")
    
    # different feature require different form of filesDict
    # merge requires fileDict length to be greater than 1. compress doesn't have any requirements.
    match get_calling_function():
        case "compress.py": 
            return validatedFilesDict
        
        case "merge.py":
            if final_validated_file_count <= 1:
                raise PrettyErrorDisplay("Excepted at least 2 pdf files for merging.")
        
            return validatedFilesDict


def return_validated_display(filesDict:dict):
    """
    Returns a Rich table as output for terminal print.
    Table only show the state of the files before operation
    Takes a dict which it expects to have absolute filename, validity, state of the file and size.
    If valid is not True, they will be displayed as X and red strikethroughs.
    
    Args:
        filesDict (dict): dict containing information of the files and their properties.

    Returns:
        str: Rich-based table output as string
    """
    from rich.table import Table
    index = 0
    validated_list_table = Table(show_lines=True)
    validated_list_table.add_column("#", justify="center", vertical="middle")
    validated_list_table.add_column("Filename", vertical="middle")
    validated_list_table.add_column("Abspath", vertical="middle", overflow="fold")
    validated_list_table.add_column("Status", vertical="middle")
    validated_list_table.add_column("Size (MB)", vertical="middle", justify="center")

    for file_item in filesDict.items(): 
        valid = file_item[1]['valid']
        file_name = file_item[0]
        basename = os.path.splitext(return_basename(file_item[0]))[0]
        state = file_item[1]['state']
        size = f"{file_item[1]['initial_size']/ (1024 * 1024):.3f}"
        if valid:
            validity = "[green]Verified[/green]" 
            index += 1
        elif valid == None:
            validity = "[yellow]Unknown[/yellow]"
            index += 1
        else:
            # state is false
            validity = state
            size = "[red]X[/red]"
            file_name = f"[strike][red]{file_name}[/strike][/red]"
            basename = f"[strike][red]{basename}[/strike][/red]"

        # Rich table doesn't take any 'int' type
        file_index = str(index) if valid == None or valid == True else "[red]X[/red]"
        validated_list_table.add_row(file_index, basename, file_name, validity, str(size))

    return validated_list_table
