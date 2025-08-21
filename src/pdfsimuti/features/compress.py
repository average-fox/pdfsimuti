import typer
import os

from typing_extensions import Annotated
from typing import List
from enum import Enum

from rich import print
from rich.table import Table
from rich.panel import Panel


from pdfsimuti.utils import PrettyErrorDisplay, validate_pdf_list, return_confirm

app = typer.Typer()

# class ghostscript_settings:
#     # def __init__(self, fileList, compatibility, custom):
#     # def __init__(self, compatibility, optimization_presets, custom):
#     def __init__(self, custom):
#         # self.fileList = fileList
#         # self.batch = "dBATCH" if len(self.fileList) > 1 else ""
#         # self.compatibility = compatibility
#         # self.custom = self.validate_gs_custom_commands(custom)
#         self.custom = custom
#         self.validate_gs_custom_commands()
#         # self.optimization_presets = optimization_presets
#         self.display()
        
    
    # def validate_gs_custom_commands(self):
    # import re
    #     compatibility_match = re.search(r'-dCompatibilityLevel=([\d.]+)', self.custom)
    #     preset_match = re.search(r'-dPDFSETTINGS=/\w+', self.custom)
    #     # external_files regex will locate all occurance of "pdf files"
    #     external_files = re.search(r'\b\w+\.pdf\b', self.custom)
        
    #     # if compatibility_match:
    #     #     self.compatibility = compatibility_match.group(1)
    #     # if preset_match:
    #     #     self.optimization_presets = preset_match.group(0)
    #     if external_files:
    #         # GhostScript is complicated. I dont know how it works so for the time being, no files via ghostscript
            # raise PrettyErrorDisplay(f"""
            #                          Ghostscript via PDFsimuti cannot have external PDF files. Please insert them outside the string
            #                          Obtained files: {external_files}  
            #                          """)
        
        # list of files
        # optimization presets: screen, ebook (default), printer, prepress
        # batch or no batch. If batch then use dNOPAUSE
        # compatibility 1.3, 1.4 (default), 1.7, 2.0
        # custom arguments (be sure to detect that sOutPut and other inputs. PDFSimUti cannot accept file items via ghostScript) 
        # custom detect: DownSampleColorImages
        # custom detect: ColorImageResolution
        
    # def display(self):
    #     print(self.custom)
        

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
    printer = "printer"
    prepress = "prepress"
    

def return_fileList_size(itemList : list) -> list:
    """
    returns a list of the file size.

    Args:
        itemList (list): list of PDFs

    Returns:
        float: total size of the list
    """
    return [round(os.path.getsize(item), 2) for item in itemList]


def display_overview_confirm(itemList: list, compressMethod) -> bool:
    """
    Compress display overview and final confirmation

    Args:
        itemList (list): list of files

    Returns:
        bool: Confirmation of compressing
    """
    
    from rich.text import Text
    from rich.console import Group
    
    print("\nThe following file(s) will be compressed.")
    
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI")
    table.add_column("File Name")
    table.add_column("File Path (Absolute)", justify="center")
    table.add_column("Size (KB)")
    
    for index, item in enumerate(itemList, 1):
        table.add_row(str(index), os.path.basename(item), os.path.abspath(item), str(os.path.getsize(item)))    
    
    panel_group = Group(
        table, 
        Text(f"Compression mode: {'GhostScript' if compressMethod == 'gs' else compressMethod.capitalize()}")   
    )
    print(Panel(panel_group, subtitle="Compress Overview", border_style="bright_cyan", expand=False, padding=(1,2)))
    
    return return_confirm("Do you want to continue with this settings?")


def display_compress_outcome(infoList : list):
    """
    Display the compress outcome

    Args:
        infoList (list): list of the PDFs
    """
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI"),
    table.add_column("File Name")
    table.add_column("File Location")
    table.add_column("Before (KB)", justify="center")
    table.add_column("After (KB)", justify="center")
    table.add_column("Compression\n [green]Green[/green]=Good\n[red]Red[/red]=Bad", justify="center")

    for index, item in enumerate(infoList, 1):
        itemName, before, after = item
        compression_calculate = abs(round((before - after)/before*100, 3))
        table.add_row(str(index), os.path.basename(itemName), os.path.dirname(itemName), str(before), str(after), f'[green]{compression_calculate}%[/green]' if before > after else f'[red]{compression_calculate}%[/red]')
        
    print(Panel(table, subtitle="Compression Completed", border_style="bright_green", expand=False))


def pymupdf_compression(fileList: list):    
    try: 
        import fitz # fitz = pymupdf

        for item in fileList:
            with fitz.open(item) as doc:
                # temp files created to solve incremental saving issue
                temp_file = item + ".temp"
                doc.save(temp_file, garbage=4, deflate=True)
            os.replace(temp_file, item)
    except Exception: raise PrettyErrorDisplay(f"Error\n{Exception}")
    
    

def gs_compression(fileList: list, gs_settings=None):
    import subprocess
    from pdfsimuti.utils import return_joined_filePath, return_absolute_filePath, return_filepath_dirname, return_filepath_basename
    from rich.progress import Progress, SpinnerColumn

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        transient=True) as progress:
        runtime = progress.add_task(description="", total=len(fileList))
        # TODO: Create a single string of the entire command once except the file.
        for item in fileList:
            # not doing this temp will result in a blank file
            temp_file = return_joined_filePath(return_filepath_dirname(item), "temp"+return_filepath_basename(item))
            command = [
                    'gswin64c',
                    '-sDEVICE=pdfwrite',
                    '-dCompatibilityLevel=1.4',
                    '-dPDFSettings=/screen',
                    '-dEmbedAllFonts=true',
                    '-dSubsetFonts=true',
                    '-dDownsampleColorImages=true',
                    '-dColorImageResolution=72',
                    '-dDownsampleGrayImages=true',
                    '-dGrayImageResolution=72',
                    '-dMonoImageResolution=300',
                    '-dNOPAUSE',
                    '-dQuiet',
                    '-dBATCH',
                    '-dSAFER',
                    f'-sOutputFile={temp_file}',
                    return_absolute_filePath(item)
                ]
            
            try:
                subprocess.run(command, check=True, capture_output=True)
                os.replace(temp_file, return_absolute_filePath(item))
                progress.log(f"[green]Compressing...[/green] {return_filepath_basename(item)}")
                progress.update(runtime, advance=1)
                
            except subprocess.CalledProcessError as e:
                raise PrettyErrorDisplay(f"GhostScript failed to run successfully.\nGhostscript Output: {e.stderr}")
        
            except FileNotFoundError as e:
                raise PrettyErrorDisplay(f"""
            Compression via GhostScript failed.
            Please check your GhostScript installation via [code]pdfsimuti checkhealth[/code]
            If the problem persists, please create an [link=https://github.com/foxtbirdy/pdfsimuti/issues/new]issue[/link].
            """)
        

def compress_pdf_list(itemList: list, compressMethod: str):
    """
    Compress pdf main function.

    Args:
        itemList (list): list of PDFs
        compressMethod (str) : Mode of compression. Either gs or pymupdf

    """
    match compressMethod:
        case 'gs': gs_compression(fileList=itemList)
        case 'ghostscript':  gs_compression(fileList=itemList)
        case 'pymupdf': pymupdf_compression(fileList=itemList)



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
    validated_pdf_list = validate_pdf_list(fileList, exclude=excludeList,  mimeCheck=mimecheck)
    # validated_pdf_list = fileList
    if len(validated_pdf_list) == 0:
        raise PrettyErrorDisplay("No compatible PDF files found for compress.")
    
    if display_overview_confirm(validated_pdf_list, compressMethod):
        
        import logging
        from rich.logging import RichHandler
        logging.basicConfig(
            level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
        )
        log = logging.getLogger("rich")
        
        # 1st Size capture
        initial_file_size = return_fileList_size(validated_pdf_list)
        
        # runtime
        log.info("Working...")
        compress_pdf_list(validated_pdf_list, compressMethod)
        log.info("Compression runtime over.")
        
        # 2nd Size Capture
        final_file_size = return_fileList_size(validated_pdf_list)

        
        # Create a list combining PDFitems, Initial Size & Final Size
        outcomeFileList = [(name, initial, final) for name, initial, final in zip(validated_pdf_list, initial_file_size, final_file_size)]
        display_compress_outcome(outcomeFileList)
    else:
        print("[red]Aborted[/red]")


def compress(
    filelist: Annotated[List[str], typer.Argument(help="PDF file(s) to be compressed. Can be single or multiple")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option("--exclude", "-x", help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    compressMethod: Annotated[compressMethodChoice, typer.Option("-cm", "--compressMethod", help="Compression application choice. Tip: 'ghostscript' can be written as 'gs'", rich_help_panel="Additional Options", metavar="[gs/ghostscript|pymupdf]")] = "pymupdf",
    compatibility: Annotated[gsCompatibilityChoice, typer.Option(help="Specify ghostscript compatibility mode", rich_help_panel="Ghostscript options")] = '1.4',
    presets: Annotated[gsPDFshrinkPresets, typer.Option(help="Specify ghostscript pdf compression presets", rich_help_panel="Ghostscript options")] = "ebook",
    gs_custom: Annotated[str, typer.Option(help="Custom commands for ghostscript. Commands must be case-sensitive", rich_help_panel="Ghostscript options")] = None
    ):
    # TODO: Do something here like configure_gs_settings(param1, param2, param3 T / F ,param 4) then pass the info to the main compress_runtime
    # gs itself is a class. Not a singple function so that it can accom udate more features.
    
    compress_runtime(filelist, mimecheck, exclude, compressMethod.value)
    # compress_pdf_list(filelist, compressMethod)
    # ghostscript_settings(gs_custom)

    
# ✅TODO: Get rid of validate from compress. Prioritize mimecheck boolean only
# ✅TODO: tidy up the codebase a bit. it's ancient
# ✅TODO: do some designings to the compress. be sure to add display_rejected_files from utils.py as well
# ✅TODO: create flag for compression. PyMuPDf by default, ghostscript or gs as option
# ✅TODO: use case statement between ghostscript and pymupdf. Both needs to have their own function and is called from compress_runtime. 
# compress_runtime will handle the passing of the fileList to compression mode
# TODO: Run basic tests with Ghostscript and PyMuPDF
# TODO: explore all features of the ghostscript and pymupdf
# TODO: add compression strength selection for pymupdf
# TODO: research preserve-files mode. (for users in case their compression choice gets them fucked up)
# TODO: preserve-files mode needs to be able to save files as PDFSIMUTI-COMPRESSED_filename.pdf
# TODO: revert_files. If compression is performed and the compress results is bigger than filesize, abort and revert to previous file. Requires preserve-Files to work
# You may delay that to v0.5.0 release
# TODO: final code tidying up
# TODO: get rid of this todo