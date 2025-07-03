import typer
import fitz
import os

from typing_extensions import Annotated
from typing import List
from rich import print
from rich.table import Table
from rich.panel import Panel

from pdfsimuti import utils

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


def compress_pdf(itemList: list):
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
    except Exception as e: raise utils.PrettyErrorDisplay(f"Program Failed To Run Properly. \n{e}")


def compress_runtime(itemList: list):
    """
    Compress runtime
    Captures list file size two times (before, after) for comparison

    Args:
        itemList (list): list of the files
    """
    # 1st Size capture
    initial_file_size = list_file_size(itemList)
    compress_pdf(itemList)
    # 2nd Size Capture
    final_file_size = list_file_size(itemList)
    # Create a list combining itemList, Initial Size & Final Size
    final = [(name, initial, final) for name, initial, final in zip(itemList, initial_file_size, final_file_size)]
    display_compress_outcome(final)


def compress(
    item: Annotated[List[str], typer.Argument(help="PDF files to be compressed")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    validate: Annotated[bool, typer.Option("--validate/--no-validate", "-v/-nv", help="Enable/Disable validation of PDF files before execution", rich_help_panel="Feature Behavior")] = True,
):
    if validate: item = utils.validate_pdf_list(item, mimecheck, exclude)
    if display_overview_confirm(item): compress_runtime(item)