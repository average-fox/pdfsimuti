import typer
import fitz # fitz = pymupdf
import os

from typing_extensions import Annotated
from typing import List
from enum import Enum

from rich import print
from rich.table import Table
from rich.panel import Panel

from pdfsimuti.utils import PrettyErrorDisplay, validate_pdf_list, return_confirm

app = typer.Typer()

class ghostscript_settings:
    def __init__(self, fileList, compatibility, custom):
        self.fileList = fileList
        self.batch = "dBATCH" if len(self.fileList) > 1 else ""
        self.compatibility = compatibility
        self.custom = self.validate_gs_custom_commands(self.custom)
        
    
    def validate_gs_custom_commands(self, custom):        
        pass
        # list of files
        # optimization presets: screen, ebook (default), printer, prepress
        # batch or no batch. If batch then use dNOPAUSE
        # compatibility 1.3, 1.4 (default), 1.7, 2.0
        # custom arguments (be sure to detect that sOutPut and other inputs. PDFSimUti cannot accept file items via ghostScript) 
        # custom detect: DownSampleColorImages
        # custom detect: ColorImageResolution
        

class compressMethodChoice(str, Enum):
    gs = "gs"
    pymupdf = "pymupdf"
    ghostscript = "ghostscript"


class gsCompatibilityChoice(str, Enum):
    one_three = "1.3"
    one_four = "1.4"
    one_seven = "1.7"
    two_zero = "2.0"


class gsPDFshrinkPresets(str, Enum):
    ebook = "ebook"
    screen = "screen"
    

def return_fileList_size(itemList : list) -> float:
    """
    Show the file size of the entire list of PDF

    Args:
        itemList (list): list of PDFs

    Returns:
        float: total size of the list
    """
    return [round(os.path.getsize(item), 2) for item in itemList]


def display_overview_confirm(itemList: list) -> bool:
    """
    Compress display overview and final confirmation

    Args:
        itemList (list): list of files

    Returns:
        bool: Confirmation of compressing
    """
    print("\nThe following files will be compressed.")
    
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI")
    table.add_column("File Name")
    table.add_column("File Path (Absolute)", justify="center")
    table.add_column("Size (KB)")
    
    for index, item in enumerate(itemList, 1):
        table.add_row(str(index), os.path.basename(item), os.path.abspath(item), str(os.path.getsize(item)))
    
    
    print(Panel(table, subtitle="Compress Overview", border_style="bright_cyan", expand=False, padding=(1,2)))
    return return_confirm("Do you want to continue with this settings?")


def display_compress_outcome(infoList : list):
    """
    Display the compress outcome

    Args:
        infoList (list): list of the PDFs
    """
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI")
    table.add_column("File Name")
    table.add_column("File Location")
    table.add_column("Before (KB)", justify="center")
    table.add_column("After (KB)", justify="center")
    table.add_column("Compression", justify="center")

    for index, item in enumerate(infoList, 1):
        itemName, before, after = item
        compression_calculate = round((before - after)/before*100, 2)
        table.add_row(str(index), itemName, os.path.dirname(itemName), str(before), str(after), f'{compression_calculate}%' if before > after else f'[red]{compression_calculate}%[/red]')
    print(Panel(table, subtitle="Successful Compression", border_style="bright_green", expand=False))


def compress_pdf_list(itemList: list, compressMethod: str):
    """
    Compress pdf main function

    Args:
        itemList (list): list of PDFs
        compressMethod (str) : Mode of compression. Either gs or pymupdf

    Raises:
        utils.PrettyErrorDisplay: raise exception if compression fails
    """
    try: 
        match compressMethod:
            case 'gs': gs_compression(fileList=itemList)
            case 'ghostscript':  gs_compression(fileList=itemList)
            case 'pymupdf': pymupdf_compression(fileList=itemList)
    except Exception as e: raise PrettyErrorDisplay(f"Program Failed To Run Properly. \n{e}")


def pymupdf_compression(fileList: list):
    for item in fileList:
        with fitz.open(item) as doc:
            # temp files created to solve incremental saving issue
            temp_file = item + ".temp"
            doc.save(temp_file, garbage=4, deflate=True)
        os.replace(temp_file, item)


def gs_compression(fileList: list):
    print("Not built yet. Please be patient.")


def compress_runtime(fileList: list, mimecheck: bool, excludeList, compressMethod: str):
    """
    Compress runtime
    Captures list file size two times (before, after) for comparison

    Args:
        fileList (list): list of the files to be compressed (unvalidated)
        mimecheck: bool enable mimechecking
        excludeList (list): list of files to be excluded (unvalidated) (don't need validation)
        compressMethod (str) : Compression mode
    """
    validated_file_list = validate_pdf_list(fileList, exclude=excludeList,  mimeCheck=mimecheck)
    
    if display_overview_confirm(validated_file_list):
        
        # 1st Size capture
        initial_file_size = return_fileList_size(validated_file_list)
        # runtime
        compress_pdf_list(validated_file_list, compressMethod)
        
        # 2nd Size Capture
        final_file_size = return_fileList_size(validated_file_list)
        
        # Create a list combining PDFitems, Initial Size & Final Size
        outcomeFileList = [(name, initial, final) for name, initial, final in zip(validated_file_list, initial_file_size, final_file_size)]
        display_compress_outcome(outcomeFileList)
    else:
        print("[red]Aborted[/red]")


def compress(
    filelist: Annotated[List[str], typer.Argument(help="PDF files to be compressed. Can be single or multiple")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option(help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    
    compressMethod: Annotated[compressMethodChoice, typer.Option("-cm", "--compressMethod", help="Compression application choice. Tip: 'ghostscript' can be written as 'gs'", rich_help_panel="Additional Options", metavar="[gs/ghostscript|pymupdf]")] = "pymupdf",
    compatibility: Annotated[gsCompatibilityChoice, typer.Option(help="Specify gs Compatibility mode", rich_help_panel="Ghostscript options")] = '1.4',
    presets: Annotated[gsPDFshrinkPresets, typer.Option(help="Specify gs pdf shrinking presets", rich_help_panel="Ghostscript options (--compressMethod gs  | --compressMethod ghostscript)")] = "ebook",
    
    ):
    # TODO: Do something here like configure_gs_settings(param1, param2, param3 T / F ,param 4) then pass the info to the main compress_runtime
    # gs itself is a class. Not a singple function so that it can accomudate more features.
    compress_runtime(filelist, mimecheck, exclude, compressMethod)
    # compress_pdf_list(filelist, compressMethod)

    
# ✅TODO: Get rid of validate from compress. Prioritize mimecheck boolean only
# ✅TODO: tidy up the codebase a bit. it's ancient
# ✅TODO: do some designings to the compress. be sure to add display_rejected_files from utils.py as well
# ✅TODO: create flag for compression. PyMuPDf by default, ghostscript or gs as option
# ✅TODO: use case statement between ghostscript and pymupdf. Both needs to have their own function and is called from compress_runtime. 
# compress_runtime will handle the passing of the fileList to compression mode
# TODO: Run basic tests with Ghostscript and PyMuPDF
# TODO: explore all features of the ghostscript and pymupdf
# TODO: research preserve-files mode. (for users in case their compression choice gets them fucked up)
# TODO: preserve-files mode needs to be able to save files as PDFSIMUTI-COMPRESSED_filename.pdf
# TODO: revert_files. If compression is performed and the compress results is bigger than filesize, abort and revert to previous file. Requires preserve-Files to work
# You may delay that to v0.5.0 release
# TODO: final code tidying up
# TODO: get rid of this todo