import os
import magic
from rich import print

from click.exceptions import ClickException
workingDir = os.getcwd() # use this var on functions that calls os.getcwd() more than once


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
    valid_file_list = []
    for item in items:
        if item not in valid_file_list and has_pdf_extension(item) and os.path.exists(item): valid_file_list.append(os.path.abspath(item))
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else item} [/yellow]")
            # Note: "." is actually an address to the current directory
            valid_file_list.extend(get_pdf_from_dir(item))
        else: print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] {item} [/i]")

    # Sorts the list previously from set to remove duplicates and checks for exclude to remove. 
    # [] is for NoneType to allow iteration of list
    valid_file_list = sorted(list(set([i for i in valid_file_list or [] if i not in (exclude or [])])))

    # Performs mimechecking of the file. Changes the list
    if mimeCheck:
        print("\n[green]File mimechecking enabled.[/green]")
        for item in valid_file_list:
            if magic.Magic(mime=True).from_file(item) != "application/pdf":
                print(f"[yellow]CAUTION! Automatic Merge Target Ignore. \n[bold red]{item}[/bold red] is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'[/yellow]")
                valid_file_list.remove(item)
    else:
        print("\n[orange]Fake PDF files cannot be detected. Use '-m' to enable file mime checking \n[/orange]")

    # List needs to be more than 1 validated pdf to work with merge
    if len(valid_file_list) <= 1: 
        raise PrettyErrorDisplay(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return valid_file_list
