import typer
import os

from typing_extensions import Annotated
from typing import List
from enum import Enum

from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group

from pdfsimuti.utils import PrettyErrorDisplay

import logging
from rich.logging import RichHandler
logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)

from pdfsimuti.utils import return_basename, return_dirname

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
        
        Custom GhostScript Commands: {"/n"+self.custom if self.custom else None}
        {"Please note, any ghostscript custom command if added can override the values represented here.\n" if self.custom is not None else ""}
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
    

def display_overview_confirm(filesDict: dict, compressInstance) -> bool:
    """
    Display a summary table of files to be compressed and the current compression settings, 
    then prompt the user for final confirmation to proceed.

    Args:
        filesDict (dict): A dictionary of validated file paths ready for compression.
        compressInstance (instance): An instance of either ``ghostscript_settings`` or ``pymupdf_settings``.

    """    
    from rich.rule import Rule
    from pdfsimuti.utils import return_validated_display

    console = Console()
    panel_group = Group(
        Rule("Compress Settings"),
        console.render_str(f"{compressInstance.display_properties()}"),
        Rule("Selected files for Compression"),
        return_validated_display(filesDict)
    )
    console.print(Panel(panel_group, subtitle="Compress Overview", border_style="bright_cyan", expand=False))


def display_compress_outcome(outcomeFilesDict : dict, time_elasped: int):
    """
    Display the results of the compression process in a formatted table, showing file size changes and total time elapsed.
    
    Compression percentage is color-coded to indicate reduction (Green) or increase (Red) in size.

    Args:
        outcomeFilesDict (dict): A dictionary mapping file paths to a tuple of (initial_size, final_size).
        time_elasped (int): The total time (in seconds) taken for the compression process.
    """
    table = Table(show_lines=True, highlight=True, )
    table.add_column("SI", vertical="middle"),
    table.add_column("File Name", vertical="middle")
    table.add_column("File Location (absolute)", vertical="middle")
    table.add_column("Before (KB)", vertical="middle", justify="center")
    table.add_column("After (KB)", vertical="middle", justify="center")
    table.add_column("Outcome", vertical="middle", justify="center")

    for index, (filename, filedata) in enumerate(outcomeFilesDict.items()):
        initial = filedata['initial']
        final =  filedata['final']
        if not filedata['validity']:
            # user removed the file during the program runtime
            table.add_row(str(index), f"[strike]{return_basename(filename)}[/strike]", f"[strike]{filename}[/strike]", "[red]ERROR[/red]", "[red]ERROR[/red]", "[red]ERROR[/red]")
        else:
            compression_calculate = abs(round((initial - final)/initial*100, 3))
            table.add_row(str(index), return_basename(filename), filename, str(initial), str(final), f'[green]{compression_calculate}%[/green]' if initial > final else f'[red]{compression_calculate}%[/red]')
            
    outcome_print_group = Group(
            table,
            f"\nTotal time taken: {round(time_elasped, 2)} seconds")
    print(Panel(outcome_print_group, subtitle="Compression Completed", border_style="bright_green", expand=False))
    

def pymupdf_compression(filesDict: list, fitz_instance):   
    """
    Execute PyMuPDF (fitz) compression on a list of PDF files with specified settings.

    The compression uses incremental saving logic with a temporary file to ensure safe operation.

    Args:
        filesDict (dict): A list of file paths to be compressed.
        fitz_instance (instance): An instance of ``pymupdf_settings`` containing the compression parameters.
    """
    # try: 

    import fitz # fitz = pymupdf
    for item in filesDict:
        try:
            with fitz.open(item) as doc:
                # temp files created to solve incremental saving issue
                temp = item + ".temp"
                doc.save(temp, garbage=fitz_instance["garbageStrength"], deflate=True, deflate_fonts=True, deflate_images=True)
            os.replace(temp, item)
        except ValueError:
            log.warn(f"CAUTION. '{return_basename(item)}' cannot be compressed")
            continue
        except Exception as e: 
            raise PrettyErrorDisplay(f"Error. PyMuPDF failed to run\n{e}")    
    

def ghostscript_compression(filesDict: list, gs_instance):
    """
    Execute PDF compression on a list of files by calling the Ghostscript command-line utility with customized settings.

    Args:
        filesDict (dict): A list of file paths to be compressed.
        gs_instance (instance): An instance of ``ghostscript_settings`` containing all Ghostscript parameters.
    """
    # special warning in case user uses something else other than colorConversion
    if gs_instance["colorConversion"] != "LeaveColorUnchanged":
        from rich.prompt import Confirm
        if not Confirm.ask(f"[bold white on red] Warning! [/bold white on red] Color Conversion not default. Colors will be affected. Proceed?"):
            raise PrettyErrorDisplay("Program terminated for safety.")   

    import subprocess
    from pdfsimuti.utils import return_joined_filePath, rtn_gs_name
    from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn ,TimeElapsedColumn

    columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ]

    with Progress(
        *columns, 
        transient=True) as progress:
        
        runtime = progress.add_task(description="GhostScript is running...", total=len(filesDict))
        log.info("Started GhostScript calling.")
        
        for target in filesDict:
            file_runtime = progress.add_task(description=f"Compressing: [yellow]{target}[/yellow]", total=None)
            # not doing this temp will result in a blank file
            target_basename = return_basename(target)
            temp = return_joined_filePath(return_dirname(target), "temp"+target_basename)
            progress.start_task(file_runtime)
            command = [
                    rtn_gs_name(),
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
                    f'-sOutputFile={temp}',
                    target
                ]
            
            # adding custom commands
            if gs_instance['custom']:
                command[2:2] = gs_instance['custom'].split()
            try:
                subprocess.run(command, check=True, capture_output=True)
                os.replace(temp, target)
                progress.log(f"[green]Compressed [/green] Filepath: {target}")
                progress.remove_task(file_runtime)
                progress.update(runtime, advance=1)
                
            except subprocess.CalledProcessError as e:
                if not os.path.exists(target):
                    log.warning(f"Filepath: {return_basename(target)} failed to compress. File not found.")
                    os.remove(temp)
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
                if os.path.exists(temp): os.remove(temp)
                exit()
                
            except Exception as e:
                raise PrettyErrorDisplay(f"GhostScript compression has failed\n{e}")
            

def compress_runtime(fileList: list, mimecheck: bool, excludeList, compressInstance=None):
    """
    Control the entire PDF compression process, including validation, user confirmation, runtime execution, and displaying results.
    The function measures and compares file sizes before and after compression to report the outcome and time elapsed.

    Args:
        fileList (list): A list of file or directory paths to be processed.
        mimecheck (bool): Boolean flag to enable/disable external MIME type validation.
        excludeList (list): A list of file paths to exclude from compression.
        compressInstance (instance): An instance of either ``ghostscript_settings`` or ``pymupdf_settings``.
    """
    from pdfsimuti.utils import return_confirm, validate_pdf_dict

    log.info("Validating files...")
    filesDict = validate_pdf_dict(fileList, exclude=excludeList,  mimeCheck=mimecheck)
    validated_pdf_dict = {key:value for key, value in filesDict.items() if value['valid'] == True}
    log.info("Validation complete")

    # Display overview
    display_overview_confirm(filesDict, compressInstance)

    if not any(value['valid'] for value in filesDict.values()):
        raise PrettyErrorDisplay("No compatible files to compress.")
    
    # create an entry like this => {file_item : (validity, initial_size, final_size)}
    outcomeFileDict = {file_item: {'validity': None, 'initial': os.path.getsize(file_item), 'final': None} for file_item in validated_pdf_dict.keys()}

    if return_confirm("\nDo you want to continue with this settings?"):
        import time
        
        # 1st Size capture
        start_time = time.time()
        # initial_file_size = [file_detail['data'] for file_detail in validated_pdf_dict.values()]
        log.info("Compression runtime started.")
        #########################################
        match compressInstance.__class__.__name__:
            case 'ghostscript_settings': ghostscript_compression(validated_pdf_dict, compressInstance)
            case 'pymupdf_settings': pymupdf_compression(validated_pdf_dict, compressInstance)
        #########################################
        log.info("Compression runtime over.")
        
        # 2nd Size Capture
        end_time = time.time()

        #### This block is created for the case of having a file being removed during runtime but akso to show that to the user
        for filename, _ in outcomeFileDict.items():
            try:
                outcomeFileDict[filename]['final'] = os.path.getsize(filename)
                outcomeFileDict[filename]['validity'] = True
            except FileNotFoundError:
                outcomeFileDict[filename]['validity'] = False

        display_compress_outcome(outcomeFileDict, end_time-start_time)
    else:
        print("[red]Aborted[/red]")


def compress(
    filelist: Annotated[List[str], typer.Argument(help="PDF file(s) to be compressed. Can be single or multiple", metavar="pdf_item")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option("--exclude", "-x", help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional options")]=None,
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
