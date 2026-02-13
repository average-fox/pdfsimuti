import typer
import os

from typing_extensions import Annotated
from typing import List
from enum import Enum

from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group

import logging
from rich.logging import RichHandler
logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
)

from pdfsimuti.utils import return_basename, return_dirname, CURRENT_DIR
from pdfsimuti.utils import PrettyErrorDisplay

app = typer.Typer()
log = logging.getLogger("rich")

class Fitz_settings:
    def __init__(self, garbageStrength):
        self.garbageStrength = garbageStrength
             
    def __getitem__(self, key):
        return getattr(self, key)
    
    def display_properties(self, preserve_choice):
        from pdfsimuti.utils import text_dedent
        return text_dedent(f"""
        Compression mode: PyMuPDF
        Preserve files: {preserve_choice}
        
        Compression Settings:
        -----------------------
        Garbage Mode: {self.garbageStrength}   
        -----------------------      
        """)


class GS_settings:
    def __init__(self, compatibility, presets ,enableEmbedFonts, enableColorSampling ,colorResValue, colorSample, enableGreySampling, greyResValue, greySample, colorConversion, custom):
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

        # process custom commands
        self.custom = custom
        self.validate_gs_custom_commands(custom)
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def validate_gs_custom_commands(self, custom_commands):
        if custom_commands != '':
            log.info("Validating custom commands")
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
        

    def display_properties(self, preserve_choice):
        from pdfsimuti.utils import text_dedent
        return text_dedent(f"""
        Compression mode: GhostScript
        Preserve files: {preserve_choice}
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
    

def display_overview_confirm(filesDict, compressInstance, preserve_choice):
    """
    Display a summary table of files to be compressed and the current compression settings, 
    then prompt the user for final confirmation to proceed.

    Args:
        filesDict (dict): A dictionary of validated file paths ready for compression.
        compressInstance (instance): An instance of either ``GS_settings`` or ``Fitz_settings``.

    """    
    from rich.rule import Rule
    from pdfsimuti.utils import return_validated_display

    console = Console()
    panel_group = Group(
        Rule("Compress Settings"),
        console.render_str(f"{compressInstance.display_properties(preserve_choice)}"),
        Rule("Selected files for Compression"),
        return_validated_display(filesDict)
    )
    console.print(Panel(panel_group, subtitle="Compress Overview", border_style="bright_cyan", expand=False))


def display_compress_outcome(outcomeFilesDict : dict, time_elasped: float):
    """
    Display the results of the compression process in a formatted table, showing file size changes and total time elapsed.
    
    Compression percentage is color-coded to indicate reduction (Green) or increase (Red) in size.

    Args:
        outcomeFilesDict (dict): A dictionary mapping file paths to a tuple of (initial_size, final_size).
        time_elasped (int): The total time (in seconds) taken for the compression process.
    """
    table = Table(show_lines=True, highlight=True)
    table.add_column("SI", vertical="middle")
    table.add_column("File Name", vertical="middle")
    table.add_column("File Location (absolute)", vertical="middle")
    table.add_column("Before (KB)", vertical="middle", justify="center")
    table.add_column("After (KB)", vertical="middle", justify="center")
    table.add_column("Outcome", vertical="middle", justify="center")

    for index, file_entry in enumerate(outcomeFilesDict.items()):
        initial = file_entry[1]['initial_size']
        final =  file_entry[1]['final_size']
        filename = file_entry[1]['saving_path']
        if not file_entry[1]['valid']:
            # user removed the file during the program runtime
            table.add_row(str(index), f"[strike]{return_basename(filename)}[/strike]", f"[strike]{filename}[/strike]", "[red]ERROR[/red]", "[red]ERROR[/red]", "[red]ERROR[/red]")
        else:
            compression_calculate = abs(round((initial - final)/initial*100, 3))
            table.add_row(str(index), return_basename(filename), filename, str(initial), str(final), f'[green]{compression_calculate}%[/green]' if initial > final else f'[red]{compression_calculate}%[/red]')
            
    outcome_print_group = Group(
            table,
            f"\nTotal time taken: {round(time_elasped, 2)} seconds")
    print(Panel(outcome_print_group, subtitle="Compression Completed", border_style="bright_green", expand=False))
    

def designate_saving_filepath(targetDict: dict):
    import datetime
    folder_path = os.path.join(CURRENT_DIR, f'pdfsimuti-compressed-files-{datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')}')

    os.mkdir(folder_path)
    for file_entry in targetDict.items():
        file_entry[1]['saving_path'] = os.path.join(folder_path, os.path.basename(file_entry[0]))
    
    return targetDict
    

def fitz_compression(filesDict: dict,  fitz_instance):
    import fitz
    
    for file_entry in filesDict.items():
        target = file_entry[0]
        target_savingPath = file_entry[1]['saving_path']
        try:
            with fitz.open(target) as doc:
                # temp files created to solve incremental saving issue
                temp = (target + ".temp") if target == target_savingPath else target_savingPath
                doc.save(temp, garbage=fitz_instance["garbageStrength"], deflate=True, deflate_fonts=True, deflate_images=True)
                file_entry[1]['final_size'] = os.path.getsize(temp)
            if target == target_savingPath: os.replace(temp, target)
        except ValueError:
            log.warning(f"CAUTION. '{return_basename(target)}' cannot be compressed")
            file_entry[1]['valid'] = False
            file_entry[1]['state'] = 'Failed to merge'
            continue
        except Exception as e: 
            raise PrettyErrorDisplay(f"Error. PyMuPDF failed to run\n{e}")    
    
    return filesDict


def gs_compression(filesDict: dict, gs_instance):
    import subprocess
    from pdfsimuti.utils import return_joined_filePath, rtn_gs_name
    from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn ,TimeElapsedColumn

    columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ]

    # special warning in case colorConversion is changed
    if gs_instance["colorConversion"] != "LeaveColorUnchanged":
        from rich.prompt import Confirm
        if not Confirm.ask(f"[bold white on red]WARNING![/bold white on red] Color Conversion not default. Colors will be affected. Proceed?"):
            raise PrettyErrorDisplay("Program terminated for safety.")   

    with Progress(
        *columns, 
        transient=True) as progress:
        
        runtime = progress.add_task(description="GhostScript is running...", total=len(filesDict))
        log.info("Started GhostScript calling.")

        for file_entry in filesDict.items():
            target = file_entry[0]
            target_runtime = progress.add_task(description=f"Compressing: [yellow]{target}[/yellow]", total=None)
            target_basename = return_basename(target)
            target_savingpath = file_entry[1]['saving_path']

            # a temp file ensures the output won't be a blank file
            temp = return_joined_filePath(return_dirname(target), "temp"+target_basename) if target == target_savingpath else target_savingpath
            progress.start_task(target_runtime)
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
                file_entry[1]['final_size'] = os.path.getsize(temp)
                if target == target_savingpath:
                    os.replace(temp, target)
                progress.log(f"[green]Compressed[/green] Filepath: {target}")
                progress.remove_task(target_runtime)
                progress.update(runtime, advance=1)
                
            except subprocess.CalledProcessError as e:
                # two types of errors can occur here. either the file got removed during operation or ghostscript failed to run.
                # if file removed during operation, script will still continue
                if not os.path.exists(target):
                    log.warning(f"Filepath: {return_basename(target)} failed to compress. File not found.")
                    os.remove(temp)
                    file_entry[1]['valid'] = False
                    file_entry[1]['state'] = 'Failed to compress'
                else:
                    raise PrettyErrorDisplay(f"""
                GhostScript failed to run.
                GhostScript Output: {e.output}
                GhostScript command: 
                {" ".join(command)}
                """)

            # is this really needed?
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
    
    return filesDict
            

def compress_runtime(fileList: list, mimecheck: bool, excludeList: list, compressInstance, preserve_choice):
    """
    Control the entire PDF compression process, including validation, user confirmation, runtime execution, and displaying results.
    The function measures and compares file sizes before and after compression to report the outcome and time elapsed.

    Args:
        fileList (list): A list of file or directory paths to be processed.
        mimecheck (bool): Boolean flag to enable/disable external MIME type validation.
        excludeList (list): A list of file paths to exclude from compression.
        compressInstance (instance): An instance of either ``GS_settings`` or ``Fitz_settings``.
    
    """
    from pdfsimuti.utils import validate_pdf_dict, return_confirm

    log.info("Validating files...")
    filesDict = validate_pdf_dict(fileList, excludeList, mimecheck)

    validated_pdf_dict = {file_entry: file_properties for file_entry, file_properties in (filesDict or {}).items() if file_properties['valid']}

    if len(validated_pdf_dict) == 0:
        raise PrettyErrorDisplay("No compatible files to compress.")
    
    log.info("Validation complete")
    
    # Display overview before confirm
    display_overview_confirm(filesDict, compressInstance, preserve_choice)


    if return_confirm("\nDo you want to continue with this settings?"):
        import time

        # 1st size capture: Initial Runtime
        start_time = time.time()
        log.info("Compression runtime started.")

        # if preserve is enabled, the save files are changed. if not, they are same value as target which meant overwrite.
        if preserve_choice: 
            validated_pdf_dict = designate_saving_filepath(validated_pdf_dict)
            print(f'Preserve choice is enabled. Files will be stored over working directory.\nSaving directory: {CURRENT_DIR}')
        
        #########################################
        match compressInstance.__class__.__name__:
            case 'GS_settings': validated_pdf_dict = gs_compression(validated_pdf_dict, compressInstance)
            case 'Fitz_settings': validated_pdf_dict = fitz_compression(validated_pdf_dict, compressInstance)
        #########################################
        log.info("Compression runtime over.")
        
        # 2nd Size Capture: Concluding Runtime
        end_time = time.time()


        # Display compress outcome.
        display_compress_outcome(validated_pdf_dict, float(end_time-start_time))
    else:
        print("[red]Aborted[/red]")


def compress(
    filelist: Annotated[List[str], typer.Argument(help="PDF file(s) to be compressed. Can be single or multiple", metavar="pdf_item")],
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option("--exclude", "-x", help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional options")]=[],
    compressMethod: Annotated[compressMethodChoice, typer.Option("-cm", "--compressMethod", help="Compression application choice. Tip: 'ghostscript' can be written as 'gs'", rich_help_panel="Additional options", metavar="[gs/ghostscript|pymupdf]")] = compressMethodChoice.pymupdf,
    preserve: Annotated[bool, typer.Option(help="Preserve file on compress. Will be saved in a folder on the working directory.", rich_help_panel='Additional options')]=False,
    garbage: Annotated[int, typer.Option(max=4, min=0, help="PyMuPDF garbage strength control", rich_help_panel="PyMuPDF Settings")] = 4,

    compatibility: Annotated[gsCompatibilityChoice, typer.Option(help="Specify ghostscript compatibility mode", rich_help_panel="GhostScript options")] = gsCompatibilityChoice.one_seven,
    presets: Annotated[gsPDFshrinkPresets, typer.Option("-p", "--presets", help="Specify ghostscript pdf compression presets", rich_help_panel="GhostScript options")] = gsPDFshrinkPresets.ebook,
    gs_custom: Annotated[str, typer.Option(help="Custom commands for ghostscript. Commands must be case-sensitive. Can override everything.", rich_help_panel="GhostScript options")] = '',
    embedFonts: Annotated[bool, typer.Option(help="Embed fonts in PDF for cross-platform font support", rich_help_panel="GhostScript options")] = True,
    colorConversion: Annotated[gsColorConversionStrategy, typer.Option("-cc", "--colorConversion", help="[red](Caution!)[/red] Change color space of the document.", case_sensitive=False, rich_help_panel="GhostScript options")] = gsColorConversionStrategy.leaveColorUnchanged,
    
    color_down:Annotated[bool, typer.Option(help="Enable reduction of color images", rich_help_panel="GhostScript options (Color Down Sampling)")] = True,
    color_res: Annotated[int, typer.Option(min=0, help="Target DPI for color image resolution. Low DPI = More pixalated", rich_help_panel="GhostScript options (Color Down Sampling)")] = 150,
    color_sample_type: Annotated[gsDownSampleControl, typer.Option("--color_sample_type", "-cs", help="Specify algorithm for downsampling", rich_help_panel="GhostScript options (Color Down Sampling)")] = gsDownSampleControl.bicubic,
    
    gray_down: Annotated[bool, typer.Option(help="Enable reduction of Black/White", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = True,
    grey_Res: Annotated[int, typer.Option(min=0, help="Target DPI for grey image resolution. Low DPI = More pixalated", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = 150,
    grey_sample_type: Annotated[gsDownSampleControl, typer.Option("--grey_sample_type", "-gs", help="Specify algorithm for downsampling", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = gsDownSampleControl.bicubic
    
    ):

    log.info("performing command line validation")
    
    import sys # detect for ghostscript commands.
    commandline_gs_exception = ["-p", '--presets', "--gs_custom", "--compatibility", "-cs", "-gs",  "--color-res", "--color_sample_type", "--color-down", "--grey-res", "--grey_down", "--grey_sample_type"]
    compressInstance = None

    if any(value in commandline_gs_exception for value in sys.argv) and compressMethod == "pymupdf":
        raise PrettyErrorDisplay("Ghostscript options cannot be added to PyMupdf compression mode.")
    
    elif compressMethod == ("gs" or "ghostscript"):
        compressInstance = GS_settings(compatibility.value, presets.value,  embedFonts, color_down, color_res, color_sample_type, gray_down, grey_Res, grey_sample_type, colorConversion.value ,gs_custom)
    
    elif compressMethod == "pymupdf":
        compressInstance = Fitz_settings(garbageStrength=garbage)

    # compress runtime handles the main load
    compress_runtime(filelist, mimecheck, exclude, compressInstance, preserve_choice=preserve)
