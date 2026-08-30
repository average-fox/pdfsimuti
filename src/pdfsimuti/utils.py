import os
import importlib
import struct # windows os + ghostScript only. Required to get CPU bit since gswin64c and gswin32c are different
import sys
from pathlib import Path

from typing import TypedDict

from rich import print
from rich.console import Console, RenderableType

from click.exceptions import ClickException
import typer

CURRENT_DIR = os.getcwd()
DEFAULT_OUTPUT = 'merged.pdf'
OPER_SYS = sys.platform

# TODO: create a log function. replace all log imports with this one.


class fileDictTyped(TypedDict):
    savingPath: Path
    valid: None | bool
    state: None | str
    initial_size: int
    final_size: int


def text_dedent(msg:str) -> str:
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
    if caution:
        confirm_once = typer.confirm("Proceed", default=False)
        if confirm_once:
            return typer.confirm("Are you sure to proceed?", default=False)
        return False
    return typer.confirm(msg, default=default)


def get_calling_function():
    # Referance: https://stackoverflow.com/questions/3711184/how-to-use-inspect-to-get-the-callers-info-from-callee-in-python
    from inspect import getouterframes
    return return_basename(getouterframes(sys._getframe(1))[1].filename)


def get_gs_name() -> str:
    gs_name = "gs"
    
    # only linux and windows environments are supported. if there are others, well open an issue then :)
    # string appending is used here. its much less complicated.
    if sys.platform == "win32":
        gs_name+="win"
        if 8*struct.calcsize("P"): gs_name+="64c"  
        else: gs_name+="32c"
        
    return gs_name
        

        
def return_basename(item: str) -> str:
    return os.path.basename(item)


def return_dirname(item:str) -> str:
    return os.path.dirname(item)


def check_file_readability(item: Path) -> bool:
    return item.is_file() and os.access(item, os.R_OK)


def return_joined_filePath(filePath1:str, filePath2:str) -> str:
    return os.path.join(filePath1, filePath2)


def txt_file_reader(fileList:list[Path]|None, sourceFile:list[Path]|None) -> list[Path]:
    changedFileList: list[Path] = []

    for item in fileList or []: changedFileList.append(Path(item))

    for sourceFileItem in sourceFile or []:
        if not sourceFileItem.suffix.lower() == ".txt": 
            print(f"[yellow]CAUTION![/yellow] External source file not .txt suffix: [yellow][i]{sourceFileItem.absolute}[/i][/yellow]")
            continue

        print(f'Reading text file: [yellow]{sourceFileItem}...[/yellow]')

        try:
            with sourceFileItem.open('r') as file:
                for line in file:
                    value = line.strip()
                    if value: changedFileList.append(Path(value))
        except FileNotFoundError:
            raise PrettyErrorDisplay(f"External file source not found: [purple]{sourceFileItem}[/purple]")
        except Exception as e:
            raise PrettyErrorDisplay(f"Error with the source file.\nError: {e}")
    
    return changedFileList


def scan_items_entry(itemList: list[Path]|None) -> list[Path]:

    return_list = []
    for item in itemList or []:
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


def returnValidatedDict(filesDict: dict[Path, fileDictTyped], mimecheck: bool):
    
    # 1. verify pymupdf 
    try:
        pymupdf = importlib.import_module('pymupdf')
    except ModuleNotFoundError:
        pymupdf = None
        print("[yellow]CAUTION![/yellow] PyMuPDF (pymupdf) not found. Skipping password protection check.")

    # 2. confirm magic exists. 
    try:
        magic = importlib.import_module('magic').Magic(mime=True) if mimecheck else None
    except ModuleNotFoundError:
        raise PrettyErrorDisplay("Package 'magic' required for mimecheck not found. Check your packages via [code]pdfsimuti checkhealth[/code]")

    # 3. start validation loop over dict
    for file_items in filesDict.items():
        target = file_items[0]
        file_mime = magic.from_file(target) if magic else None
        # 3.1. get size of the file
        try:
            file_items[1]["initial_size"] = Path(target).stat().st_size
        except Exception:
            file_items[1]['valid'] = False
            file_items[1]['state'] = 'ERROR'

        # 3.2. check file readability
        if not check_file_readability(target):
            file_items[1]['valid'] = False
            file_items[1]['state'] = "Unreadable file"

        # 3.3. check file mime
        elif magic and file_mime != "application/pdf":
            file_items[1]['valid'] = False
            file_items[1]['state'] = f"Mimecheck pass failed.\nReceived:[yellow]\n{file_mime}[/yellow]"

        # 3.4. check password protection (uses pymupdf)
        elif pymupdf:
            try:
                if pymupdf.open(file_items[0]).needs_pass:
                    file_items[1]['valid'] = False
                    file_items[1]['state'] = 'Password Protected'
            except pymupdf.FileDataError:
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

            
def validate_pdf_dict(items:list[Path]|None, source:list[Path]|None, exclude:list[Path]|None, excludeSource:list[Path]|None, mimecheck:bool):

    items = txt_file_reader(items, source) if source else items
    exclude= txt_file_reader(exclude, excludeSource) if excludeSource else exclude
    
    unvalidated_files:list[Path] = scan_items_entry(items) or []
    excludeList:list[Path] = scan_items_entry(exclude) if exclude else []

    if not mimecheck: print("[yellow]CAUTION![/yellow] Mimechecking disabled! Corrupted files can disrupt the process.")  

    # TODO: fix this annotation above the callings
    excludeFreeFilesDict = [
        Path(file_entry) for file_entry in unvalidated_files
        if file_entry not in excludeList
    ]

    newFilesDict: dict[Path, fileDictTyped] = {
        file_entry: {
            "savingPath": file_entry,
            "valid": None,
            "state": None,
            "initial_size": 0,
            "final_size": 0,
        }
        for file_entry in excludeFreeFilesDict
    }

    validatedFilesDict = returnValidatedDict(newFilesDict, mimecheck)

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


def returnValidDisplayRenderable(filesDict:dict[Path, fileDictTyped]) -> RenderableType:

    from rich.table import Table
    index = 0
    validated_list_table = Table(show_lines=True)
    validated_list_table.add_column("#", justify="center", vertical="middle")
    validated_list_table.add_column("Filename", vertical="middle")
    validated_list_table.add_column("Abspath", vertical="middle", overflow="fold")
    validated_list_table.add_column("Status", vertical="middle")
    validated_list_table.add_column("Size (MB)", vertical="middle", justify="center")

    for file_item in filesDict.items(): 
        valid = file_item[1]["valid"]
        file_name = str(file_item[0])
        basename = Path(file_name).name
        validity = file_item[1]['state']
        size = f"{file_item[1]['initial_size']/ (1024 * 1024):.3f}"
        if valid:
            validity = "[green]Verified[/green]" 
            index += 1
        elif valid == None:
            validity = "[yellow]Unknown[/yellow]"
            index += 1
        else:
            # state is false
            size = "[red]X[/red]"
            file_name = f"[strike][red]{file_name}[/strike][/red]"
            basename = f"[strike][red]{basename}[/strike][/red]"

        # Rich table doesn't take any 'int' type
        file_index = str(index) if valid == None or valid == True else "[red]X[/red]"
        validated_list_table.add_row(file_index, basename, file_name, validity, str(size))

    return validated_list_table
