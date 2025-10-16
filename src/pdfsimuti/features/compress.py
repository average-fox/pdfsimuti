import typer
import os

from typing_extensions import Annotated
from typing import List
from enum import Enum

from rich import print
from rich.table import Table
from rich.panel import Panel

from pdfsimuti.utils import PrettyErrorDisplay

import logging
from rich.logging import RichHandler
logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)

from pdfsimuti.utils import return_filepath_basename, return_filepath_dirname, return_absolute_path

app = typer.Typer()
log = logging.getLogger("rich")    


class pymupdf_settings:
    def __init__(self, garbageStrength):
        self.garbageStrength = garbageStrength
        
            
    def __getitem__(self, key):
        return getattr(self, key)
    
    
    def display_properties(self):
        from pdfsimuti.utils import text_dedent
        return text_dedent(f"""
        Compression mode: PyMuPDF
        
        Compression Settings:
        -----------------------
        Garbage Mode: {self.garbageStrength}   
        -----------------------      
        """)


class ghostscript_settings:
    def __init__(self, compatibility, presets, enableEmbedFonts, enableColorSampling ,colorResValue, colorSample, enableGreySampling, greyResValue, greySample, colorConversion, custom):
        self.compatibility = compatibility
        self.presets = presets
        self.embedAllFonts = str(enableEmbedFonts).lower()
        self.enableColorSampling = str(enableColorSampling).lower()
        self.colorResValue = colorResValue
        self.colorSample = colorSample.capitalize()
        self.enableGreySampling = str(enableGreySampling).lower()
        self.greyResValue = greyResValue
        self.greySample = greySample.capitalize()
        self.colorConversion = colorConversion
        self.custom = custom
        self.validate_gs_custom_commands(custom)


    
    def __getitem__(self, key):
        return getattr(self, key)

    
    def validate_gs_custom_commands(self, custom_commands):
        if custom_commands:
            log.info("validating custom commands")
            import re
            # external_files regex will locate all occurance of "pdf files"
            external_files = re.search(r'\b\w+\.pdf\b',custom_commands)
            if external_files:
                # GhostScript is complicated. Having external files via ghostscript is hazard. External files can only be added outside gs_custom
                # if this feature is needed, open up an issue to fix the problem.
                log.error("Invalid command found")
                raise PrettyErrorDisplay(f"""
                    Ghostscript via PDFsimuti cannot have external PDF files. Please insert them outside of --gs-custom.
                    Command: '{custom_commands}'  
                """)
        else:
            return " "
        
    def display_properties(self):
        from pdfsimuti.utils import text_dedent
        return text_dedent(f"""
        Compression mode: GhostScript
        
        Compression Settings:
        -----------------------
        Compatibility: {self.compatibility}
        Presets: {self.presets}
        Enable -dEmbedAllFonts: {self.embedAllFonts}
        Enable -dEnableColorSampling: {self.enableColorSampling}
        Enable -dEnableGreySampling: {self.enableGreySampling}
        
        Color Resolution value: {self.colorResValue}
        Color Resolution mode: {self.colorSample}
        Color Conversion Strategy: {self.colorConversion}
        
        Grey Resolution value: {self.greyResValue}
        Grey Resolution mode: {self.greySample}
        
        Custom GhostScript Commands: 
        {self.custom if self.custom else None}
        
        Please note, any ghostscript custom command if added can override the values represented here.
        -----------------------
        """)

        
class compressMethodChoice(str, Enum):
    """
    Compress method choices. Required for typer Enum options

    Args:
        str (str): typer string to match
        Enum (enum): strings to point
    """
    gs = "gs"
    pymupdf = "pymupdf"
    ghostscript = "ghostscript"



class gsColorConversionStrategy(str, Enum):
    """
    GhostScript conversion Strategy choices. Required for typer Enum options

    Args:
        str (str): typer string to match
        Enum (enum): strings to point
    """
    leaveColorUnchanged="LeaveColorUnchanged"
    Gray="Gray"
    RGB="RGB"
    CMYK="CMYK"


class gsCompatibilityChoice(str, Enum):
    """
    GhostScript compatibility settings. Required for typer Enum options

    Args:
        str (str): typer string to match
        Enum (enum): strings to point
    """
    one_three = "1.3"
    one_four = "1.4"
    one_seven = "1.7"
    two_zero = "2.0"


class gsPDFshrinkPresets(str, Enum):
    """
    GhostScript shrinking presets. Required for typer Enum options

    Args:
        str (str): typer string to match
        Enum (enum): strings to point
    """
    ebook = "ebook"
    screen = "screen"
    printer = "printer"
    prepress = "prepress"


class gsDownSampleControl(str, Enum):
    """
    GhostScript color/grey downgrading sample control. Required for typer Enum options

    Args:
        str (str): typer string to match
        Enum (enum): strings to point
    """    

    subsample = "subsample"
    average = "average"
    bicubic = "bicubic"
    

def return_fileList_size(fileDict : dict) -> list:
    """
    """
    list_size = []
    for item in fileDict:
        if os.path.exists(item):
            list_size.append(os.path.getsize(item))
        else:
            list_size.append(None)
    
    return list_size
    

def display_overview_confirm(filesDict: dict, compressInstance) -> bool:
    """
    Compress display overview and final confirmation

    Args:
        filesDict (dict): 
        compressInstance (class instance): Either ghostscript_settings or pymupdf_settings

    Returns:
        bool: Confirmation of compressing
    """
    
    from rich.console import Group
    from rich.console import Console
    from pdfsimuti.utils import return_confirm
    
    print("\nThe following file(s) will be compressed.")
    print(filesDict)
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI")
    table.add_column("File Name")
    table.add_column("File Path (Absolute)", justify="center")
    table.add_column("Size (KB)")
    
    
    for index, item in enumerate(filesDict):
        print(item)
        table.add_row(str(index+1), return_filepath_basename(item), item, str(os.path.getsize(item)))    
    
    panel_group = Group(
        Console().render_str(f"{compressInstance.display_properties()}"),
        table, 
    )
    print(Panel(panel_group, subtitle="Compress Overview", border_style="bright_cyan", expand=False, padding=(1,2)))
    
    return return_confirm("\nDo you want to continue with this settings?")


def display_compress_outcome(outcomeFilesDict : dict, time_elasped):
    """
    Display the compress outcome

    Args:
        outcomeFilesDict (dict): dicts of the PDF files.
        time_elasped (int): time taken for compression
    """
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI"),
    table.add_column("File Name")
    table.add_column("File Location (absolute)")
    table.add_column("Before (KB)", justify="center")
    table.add_column("After (KB)", justify="center")
    table.add_column("Compression\n [green]Green[/green]=Good\n[red]Red[/red]=Bad", justify="center")

    for index, (filename, (initial_size, final_size)) in enumerate(outcomeFilesDict.items(), 1):
        if os.path.exists(filename):
            compression_calculate = abs(round((initial_size - final_size)/initial_size*100, 3))
            table.add_row(str(index), return_filepath_basename(filename), filename, str(initial_size), str(final_size), f'[green]{compression_calculate}%[/green]' if initial_size > final_size else f'[red]{compression_calculate}%[/red]')
        else:
            # user removed the file during the program runtime
            table.add_row(str(index), f"[strike]{return_filepath_basename(filename)}[/strike]", f"[strike]{filename}[/strike]", "[red]ERROR[/red]", "[red]ERROR[/red]", "[red]ERROR[/red]")
    
    print(Panel(table, subtitle="Compression Completed", border_style="bright_green", expand=False))
    print(f"Total time taken: {round(time_elasped, 2)} seconds")
    

def pymupdf_compression(filesDict: list, fitz_instance):   
    """
    PyMuPDF Commpression call and runtime.
    
    Args:
        fileList (list): list of the pdf files for conversion 
    """ 
    # try: 
    print(filesDict)
    import fitz # fitz = pymupdf
    for item in filesDict:
        try:
            with fitz.open(item) as doc:
                # temp files created to solve incremental saving issue
                temp_file = item + ".temp"
                doc.save(temp_file, garbage=fitz_instance["garbageStrength"], deflate=True, deflate_fonts=True, deflate_images=True)
            os.replace(temp_file, item)
        except ValueError:
            log.warn(f"CAUTION. '{return_filepath_basename(item)}' cannot be compressed")
            continue
        except Exception as e: 
            raise PrettyErrorDisplay(f"Error. PyMuPDF failed to run\n{e}")    
    

def ghostscript_compression(filesDict: list, gs_instance):
    """
    GhostScript Commpression call and runtime.
    
    Args:
        fileList (list): list of the pdf files for conversion 
    """
    # special warning in case user uses something else other than colorConversion
    if gs_instance["colorConversion"] != "LeaveColorUnchanged":
        from rich.prompt import Confirm
        if not Confirm.ask(f"[bold white on red] Warning! [/bold white on red] Color Conversion not default. Colors will be affected. Proceed?"):
            raise PrettyErrorDisplay("Program terminated for safety.")   

    import subprocess
    from pdfsimuti.utils import return_joined_filePath, return_ghostscript_callname
    from rich.progress import Progress, SpinnerColumn

    with Progress(
        SpinnerColumn(),
        *Progress.get_default_columns(),
        transient=True) as progress:
        
        runtime = progress.add_task(description="GhostScript is running...", total=len(filesDict))
        log.info("Started GhostScript calling.")
        
        # TODO : work on this please. fix the items and remove unnecessary codes
        for target_filename in filesDict:
            # not doing this temp will result in a blank file
            target_filename_basename = return_filepath_basename(target_filename)
            temp_file = return_joined_filePath(return_filepath_dirname(target_filename), "temp"+target_filename_basename)
            print(temp_file)
            command = [
                    return_ghostscript_callname(),
                    '-sDEVICE=pdfwrite',
                    f'-dCompatibilityLevel={gs_instance['compatibility']}',
                    f'-dEmbedAllFonts={gs_instance['embedAllFonts']}',
                    f'-dColorConversionStrategy=/{gs_instance['colorConversion']}',
                    f'-dDownsampleColorImages={gs_instance['enableColorSampling']}',
                    f'-dColorImageResolution={gs_instance['colorResValue']}',
                    f'-dColorImageDownsampleType=/{gs_instance['colorSample']}',
                    f'-dDownsampleGrayImages={gs_instance['enableGreySampling']}',
                    f'-dGrayImageResolution={gs_instance['greyResValue']}',
                    f'-dGrayImageDownsampleType=/{gs_instance['greySample']}',
                    f'-dPDFSettings=/{gs_instance['presets']}',
                    '-dNOPAUSE',
                    '-dQuiet',
                    '-dBATCH',
                    '-dSAFER',
                    f'-sOutputFile={temp_file}',
                    target_filename
                ]
            
            # adding custom commands
            if gs_instance['custom']:
                command[2:2] = gs_instance['custom'].split()
            try:
                subprocess.run(command, check=True, capture_output=True)
                os.replace(temp_file, target_filename)
                progress.log(f"[green]Compressed [/green] {target_filename_basename}")
                progress.update(runtime, advance=1)
                
            except subprocess.CalledProcessError as e:
                if not os.path.exists(target_filename):
                    log.warn(f"Failed to compress {return_filepath_basename(target_filename)}. File not found.")
                else:
                    raise PrettyErrorDisplay(f"""
                GhostScript failed to run.
                GhostScript Output: {e.output}
                GhostScript command: 
                {" ".join(command)}
                """)

            except FileNotFoundError as e:
                raise PrettyErrorDisplay(f"""
            Compression via GhostScript failed.
            Please check your GhostScript installation via [code]pdfsimuti checkhealth[/code]
            If the problem persists, please create an [link=https://github.com/foxtbirdy/pdfsimuti/issues/new]issue[/link].
            """)
                
            except KeyboardInterrupt:
                print("[red]Aborting...[/red]")
                if os.path.exists(temp_file): os.remove(temp_file)
                exit()
                
            except Exception as e:
                raise PrettyErrorDisplay("GhostScript compression has failed")
                

# def compress_pdf_dict(itemList: list, compressInstance):
#     """
#     Compress pdf main function.

#     Args:
#         itemList (list): list of PDFs
#         compressMethod (str) : Mode of compression. Either gs or pymupdf
#         compressInstance : Compression settings. Can be either pymupdf or ghostscript

#     """
#     match compressInstance.__class__.__name__:
#         case 'ghostscript_settings': ghostscript_compression(itemList, compressInstance)
#         case 'pymupdf_settings': pymupdf_compression(itemList, compressInstance)



def compress_runtime(filesDict: list, mimecheck: bool, excludeList, compressInstance=None):
    """
    Compress runtime
    Captures list file size two times (before, after) for comparison
    Display time elapsed as well

    Args:
        filesDict (list): list of the files to be compressed
        mimecheck: bool enable mimechecking
        excludeList (list): list of files to be excluded
        compressMethod (str) : Compression mode
        compressInstance (class) : Class instance that carries the settings for a specific compression
    """
    from pdfsimuti.utils import validate_pdf_dict
    
    log.info("Validating files...")
    validated_pdf_dict = validate_pdf_dict(filesDict, exclude=excludeList,  mimeCheck=mimecheck)
    log.info("Validation complete")
    
    if display_overview_confirm(validated_pdf_dict, compressInstance):
        import time
        
        # 1st Size capture
        start = time.time()
        print(validated_pdf_dict)
        initial_file_size = [details['data'] for details in validated_pdf_dict.values()]
        
        log.info("Compression runtime started.")
        #########################################
        match compressInstance.__class__.__name__:
            case 'ghostscript_settings': ghostscript_compression(validated_pdf_dict, compressInstance)
            case 'pymupdf_settings': pymupdf_compression(validated_pdf_dict, compressInstance)
        #########################################
        log.info("Compression runtime over.")
        
        # 2nd Size Capture
        end = time.time()
        final_file_size = [details['data'] for details in validated_pdf_dict.values()]

        # create an entry like this => {file_item : (initial_size, final_size)}
        outcomeFileDict = {file_item : (initial_size, final_size) for file_item, initial_size, final_size in zip(validated_pdf_dict.keys(), initial_file_size, final_file_size)}
        display_compress_outcome(outcomeFileDict, end-start)
    else:
        print("[red]Aborted[/red]")


def compress(
    filelist: Annotated[List[str], typer.Argument(help="PDF file(s) to be compressed. Can be single or multiple", metavar="pdf_item")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option("--exclude", "-x", help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional options")]=[None],
    compressMethod: Annotated[compressMethodChoice, typer.Option("-cm", "--compressMethod", help="Compression application choice. Tip: 'ghostscript' can be written as 'gs'", rich_help_panel="Additional options", metavar="[gs/ghostscript|pymupdf]")] = "pymupdf",
    
    garbage: Annotated[int, typer.Option(max=4, min=0, help="PyMuPDF garbage strength control", rich_help_panel="PyMuPDF Settings")] = 4,
    
    compatibility: Annotated[gsCompatibilityChoice, typer.Option(help="Specify ghostscript compatibility mode", rich_help_panel="GhostScript options")] = '1.7',
    presets: Annotated[gsPDFshrinkPresets, typer.Option("-p", "--presets", help="Specify ghostscript pdf compression presets", rich_help_panel="GhostScript options")] = "ebook",
    gs_custom: Annotated[str, typer.Option(help="Custom commands for ghostscript. Commands must be case-sensitive. Can override everything.", rich_help_panel="GhostScript options")] = None,
    embedFonts: Annotated[bool, typer.Option(help="Embed fonts in PDF for cross-platform font support", rich_help_panel="GhostScript options")] = True,
    colorConversion: Annotated[gsColorConversionStrategy, typer.Option("-cc", "--colorConversion", help="Change color space of the document.", case_sensitive=False, rich_help_panel="GhostScript options")] = "LeaveColorUnchanged",
    
    color_down:Annotated[bool, typer.Option(help="Enable reduction of color images", rich_help_panel="GhostScript options (Color Down Sampling)")] = True,
    color_res: Annotated[int, typer.Option(min=0, help="Target DPI for color image resolution. Low DPI = More pixalated", rich_help_panel="GhostScript options (Color Down Sampling)")] = 150,
    color_sample_type: Annotated[gsDownSampleControl, typer.Option("--color_sample_type", "-cs", help="Specify algorithm for downsampling", rich_help_panel="GhostScript options (Color Down Sampling)")] = "bicubic",
    
    gray_down: Annotated[bool, typer.Option(help="Enable reduction of Black/White", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = True,
    grey_Res: Annotated[int, typer.Option(min=0, help="Target DPI for grey image resolution. Low DPI = More pixalated", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = 150,
    grey_sample_type: Annotated[gsDownSampleControl, typer.Option("--grey_sample_type", "-gs", help="Specify algorithm for downsampling", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = "bicubic"
    
    ):

    log.info("performing command line validation")
    
    import sys # detect for ghostscript commands.
    commandline_gs_exception = ["-p", '--presets', "--gs_custom", "--compatibility", "-cs", "-gs",  "--color-res", "--color_sample_type", "--grey-res", "--grey_sample_type"]
    compressInstance = None

    if any(value in commandline_gs_exception for value in sys.argv) and compressMethod == "pymupdf":
        raise PrettyErrorDisplay("Ghostscript options cannot be added to PyMupdf compression mode.")
    
    elif compressMethod == ("gs" or "ghostscript"):
        compressInstance = ghostscript_settings(compatibility.value, presets.value, embedFonts, color_down, color_res, color_sample_type, gray_down, grey_Res, grey_sample_type, colorConversion.value ,gs_custom)
    
    elif compressMethod == "pymupdf":
        compressInstance = pymupdf_settings(garbageStrength=garbage)

    # compress runtime handles the main load
    compress_runtime(filelist, mimecheck, exclude, compressInstance)