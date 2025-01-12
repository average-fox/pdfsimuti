import typer
import magic
import fitz
import os

from click.exceptions import ClickException
from typing_extensions import Annotated
from typing import List
from rich import print
from rich.table import Table
from rich.panel import Panel


app = typer.Typer()
table = Table()
workingDir = os.getcwd()


class PrettyErrorDisplay(ClickException):
    """
    Raised when the program does something it wasn't supposed to.
     
    Imports from Click.exceptions.ClickException
    """


def hasPdfExtension(item) -> bool:
    """
    Returns the filetype by checking if it endswith .pdf
    Doesn't use name.endswith("pdf") because files like file/pdf returns True if used.
    Will return false if the item is just "pdf" and nothing else
    """
    return item.lower().split(".")[-1] == "pdf" and item != "pdf"


def getFileFullPath(folderpath, filename) -> str:
    """
    Returns absolute path of a file using os.path.join
    """
    return os.path.join(folderpath, filename)


def getFilesSize(itemList):
    return [round(os.path.getsize(item)/ (1024 * 1024), 2) for item in itemList]


def getPDFfromDirectory(directory) -> list:
    """
    Gets PDFs from a directory. Only used in the validateListForPDF when the user passes a directory address instead of the filename
    """
    directory = workingDir if "." in directory else directory
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = getFileFullPath(directory, folder_item)
        if hasPdfExtension(folder_path): pdf_files.append(folder_path)

    return pdf_files


def validateListForPDF(items, mimecheck, exclude) -> list:
    """List Validation of eligible PDF files

    Args:
        items (list): Unchecked list of str as file path
        exclude (list) : List of excluded files that will remove from items
        mimecheck (bool): mimecheck of files using bool

    Raises:
        PrettyErrorDisplay: Typer Exception if list has less than 2 PDF files

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
    # Performs mimechecking of the file. Changes the list
    if mimecheck:
        print("\n[green]File mimechecking enabled.[/green]")
        for item in validFileItems:
            if magic.Magic(mime=True).from_file(item) != "application/pdf":
                print(f"[yellow]CAUTION! Automatic Merge Target Ignore. [bold red]{item}[/bold red] is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'[/yellow]")
                validFileItems.remove(item)
    else:
        print("\n[orange]Fake PDF files cannot be detected. Use '-m' to enable file mime checking \n[/orange]")
    return validFileItems


def display_overview_confirm(itemList: list) -> bool:
    print(Panel("\n".join(str(item) for item in itemList), subtitle="Compress Overview", border_style="bright_cyan", expand=False, padding=(1,2)))
    return typer.confirm("Do you want to continue with this settings?")


def displayCompressOutcome(infoList : list):
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI")
    table.add_column("Name")
    table.add_column("Before (MB)")
    table.add_column("After (MB)")
    table.add_column("Compression")

    for index, item in enumerate(infoList, 1):
        itemName, before, after = item
        compression_calculate = f'{(before - after)/before*100}%' if before > after else f'[red]{(before - after)/before*100}%[/red]'
        table.add_row(str(index), itemName, str(before), str(after), compression_calculate)
    print(Panel(table, subtitle="Successful Compression", border_style="bright_green", expand=False))


def compressPdf(itemList: list):
    try:
        for item in itemList:
            with fitz.open(item) as doc:
                # temp files created to solve incremental saving issue
                temp_file = item + ".temp"
                doc.save(temp_file, garbage=4, deflate=True)
            os.replace(temp_file, item)
    except Exception as e: raise PrettyErrorDisplay(f"Program failed to run without errors. \n{e}")


def compress_runtime(itemList: list):
    # 1st Size capture
    initial_file_size = getFilesSize(itemList)
    compressPdf(itemList)
    # 2nd Size Capture
    final_file_size = getFilesSize(itemList)
    # Create a list combining itemList, Initial Size & Final Size
    final = [(name, initial, final) for name, initial, final in zip(itemList, initial_file_size, final_file_size)]
    displayCompressOutcome(final)


def compress(
    item: Annotated[List[str], typer.Argument(help="PDF files to be compressed")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    validate: Annotated[bool, typer.Option("--validate/--no-validate", "-v/-nv", help="Enable/Disable validation of PDF files before execution", rich_help_panel="Feature Behavior")] = True,
):
    if validate: item = validateListForPDF(item, mimecheck, exclude)
    if display_overview_confirm(item): compress_runtime(item)