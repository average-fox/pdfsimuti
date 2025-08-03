import typer
import fitz # fitz = pymupdf
import os

from typing_extensions import Annotated
from typing import List

from rich import print
from rich.table import Table
from rich.panel import Panel

from pdfsimuti.utils import PrettyErrorDisplay, validate_pdf_list

app = typer.Typer()
table = Table()


def list_file_size(itemList : list) -> float:
    """
    Show the file size of the entire list of PDF

    Args:
        itemList (list): list of PDFs

    Returns:
        float: total size of the list
    """
    return [round(os.path.getsize(item)/ (1024 * 1024), 2) for item in itemList]


def display_overview_confirm(itemList: list) -> bool:
    """
    Compress display overview and final confirmation

    Args:
        itemList (list): list of files

    Returns:
        bool: Confirmation of compressing
    """
    print(Panel("\n".join(str(item) for item in itemList), subtitle="Compress Overview", border_style="bright_cyan", expand=False, padding=(1,2)))
    return typer.confirm("Do you want to continue with this settings?")


def display_compress_outcome(infoList : list):
    """
    Display the compress outcome

    Args:
        infoList (list): list of the PDFs
    """
    print(infoList)
    
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


def compress_pdf_list(itemList: list):
    """
    Compress pdf main function

    Args:
        itemList (list): list of PDFs

    Raises:
        utils.PrettyErrorDisplay: raise exception if compression fails
    """
    try:
        for item in itemList:
            with fitz.open(item) as doc:
                # temp files created to solve incremental saving issue
                temp_file = item + ".temp"
                doc.save(temp_file, garbage=4, deflate=True)
            os.replace(temp_file, item)
    except Exception as e: raise PrettyErrorDisplay(f"Program Failed To Run Properly. \n{e}")


def compress_runtime(fileList: list, mimecheck: bool, excludeList):
    """
    Compress runtime
    Captures list file size two times (before, after) for comparison

    Args:
        fileList (list): list of the files to be compressed (unvalidated)
        mimecheck: bool enable mimechecking
        excludeList (list): list of files to be excluded (unvalidated) (don't need validation)
    """
    validated_file_list = validate_pdf_list(fileList, exclude=excludeList,  mimeCheck=mimecheck)
    
    if display_overview_confirm(validated_file_list):
        # 1st Size capture
        initial_file_size = list_file_size(fileList)
        compress_pdf_list(fileList)
        # 2nd Size Capture
        final_file_size = list_file_size(fileList)
        # Create a list combining PDFitems, Initial Size & Final Size
        outcomeFileList = [(name, initial, final) for name, initial, final in zip(fileList, initial_file_size, final_file_size)]
        display_compress_outcome(outcomeFileList)
    else:
        print("[red]Job terminated.[/red]")


def compress(
    filelist: Annotated[List[str], typer.Argument(help="PDF files to be compressed. Can be single or multiple")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    ):    
    compress_runtime(filelist, mimecheck, exclude)

    
# TODO: Get rid of validate from compress. Prioritize mimecheck boolean only
# TODO: tidy up the codebase a bit. it's ancient
# TODO: do some designings to the compress. be sure to add display_rejected_files from utils.py as well
# TODO: create flag for compression. PyMuPDf by default, ghostscript or gs as option
# TODO: use case statement between ghostscript and pymupdf. Both needs to have their own function and is called from compress_runtime. 
# compress_runtime will handle the passing of the fileList to compression mode
# TODO: explore new methods on how to 
# TODO: research preserve-files mode. (for users in case their compression choice gets them fucked up)
# TODO: preserve-files mode needs to be able to save files as PDFSIMUTI-COMPRESSED_filename.pdf
# TODO: final code tidying up
# TODO: get rid of this todo 