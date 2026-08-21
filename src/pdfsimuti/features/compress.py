import typer
import os

from typing import List, Annotated, Optional
from enum import Enum

from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Console, Group

import logging
from rich.logging import RichHandler
logging.basicConfig(
    level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler(markup=True)]
)

from pdfsimuti.utils import return_basename, return_dirname, CURRENT_DIR
from pdfsimuti.utils import PrettyErrorDisplay, text_dedent

app = typer.Typer()
log = logging.getLogger("rich")
pymupdf = None
subprocess = None

def initialize_pymupdf():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore worker's warnings

    global pymupdf
    if pymupdf is None:
        import pymupdf as _pymupdf
        pymupdf = _pymupdf


def initialize_gs():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore worker's warnings

    import subprocess as sp
    global subprocess

    if subprocess is None: subprocess = sp


class pymupdf_settings:
    def __init__(self, garbageStrength):
        self.garbageStrength = garbageStrength
             
    def __getitem__(self, key):
        return getattr(self, key)
    
    def display_properties(self, preserve_choice):
        return text_dedent(f"""
        Compression mode: PyMuPDF
        Preserve files: {preserve_choice}
        {f"Preserve folder creation: " + CURRENT_DIR if preserve_choice else ""}
        
        Compression Settings:
        -----------------------
        Garbage Mode: {self.garbageStrength}   
        -----------------------      
        """)


class gs_settings:
    def __init__(self, gs_name, compatibility, presets ,enableEmbedFonts, enableColorSampling ,colorResValue, colorSample, enableGreySampling, greyResValue, greySample, colorConversion, custom):
        self.gs_name = gs_name
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
        return text_dedent(f"""
        Compression mode: GhostScript
        -----------------------
        Preserve files: {preserve_choice}
        {f"Preserve folder creation: " + CURRENT_DIR if preserve_choice else ""}
        -----------------------
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
    

def display_overview_confirm(filesDict, compressSettings, preserve_choice):
    """
    Display a summary table of files to be compressed and the current compression settings, 
    then prompt the user for final confirmation to proceed.

    Args:
        filesDict (dict): A dictionary of validated file paths ready for compression.
        compressSettings (instance): An instance of either ``gs_settings`` or ``pymupdf_settings``.
    """    
    from rich.rule import Rule
    from pdfsimuti.utils import return_validated_display

    console = Console()
    panel_group = Group(
        Rule("Compress Settings"),
        console.render_str(f"{compressSettings.display_properties(preserve_choice)}"),
        Rule("Selected files for Compression"),
        return_validated_display(filesDict)
    )
    console.print(Panel(panel_group, subtitle="Compress Overview", border_style="bright_cyan", expand=False))


def display_compress_outcome(filesDict : dict, time_elasped: float):
    """
    Display the results of the compression process in a formatted table, showing file size changes and total time elapsed.
    Compression percentage is color-coded to indicate reduction (Green) or increase (Red) in size.

    Display format:
        filename (absolute), filename (basename), initial size, final size, outcome

    Args:
        filesDict (dict): Dict that contains the files absolute path and their properties. func() requires filename, initial_size and final_size
        time_elasped (float): The total time (in seconds) taken for the compression process.
    """
    result_reverted = False
    failed_count = 0
    
    table = Table(show_lines=True, highlight=True, expand=True)
    table.add_column("#", vertical="middle")
    table.add_column("File Name", overflow="fold")
    table.add_column("File Location (absolute)", overflow="fold")
    table.add_column("Before", vertical="middle", justify="center")
    table.add_column("After", vertical="middle", justify="center")
    table.add_column("Outcome", vertical="middle", justify="center")

    for index, file_entry in enumerate(filesDict.items()):
        index += 1
        initial_size = file_entry[1]['initial_size']/1048576
        final_size =  file_entry[1]['final_size']/1048576
        filename = file_entry[1]['saving_path']

        if not file_entry[1]['valid'] or final_size == 0:
            failed_count += 1
            if file_entry[1]['state'] == 'Unchanged':
                result_reverted = True
                table.add_row(str(index), f"[yellow]{return_basename(filename)}[/yellow]", f"{filename}", "[yellow]Skipped[/yellow]", "[yellow]Skipped[/yellow]", f"[yellow]{file_entry[1]['state']}[/yellow]")
            else: 
                table.add_row(str(index), f"[strike][red]{return_basename(filename)}[/red][/strike]", f"[strike]{filename}[/strike]", "[red]FAILED[/red]", "[red]FAILED[/red]", f"[red]{file_entry[1]['state']}[/red]")
        else:
            compression_calculate = str(abs(round((initial_size - final_size)/initial_size*100, 5)))
            table.add_row(str(index), return_basename(filename), filename, str(round(initial_size,3))+ " MB", str(round(final_size,3))+ " MB", f'[green]{"-"+compression_calculate}%[/green]' if initial_size > final_size else f'[red]{"+"+compression_calculate}%[/red]')

    messenge = (
        text_dedent(f"""
        [yellow]CAUTION![/yellow] Some files were not compressed. Unchanged files are not affected
        Total Processed: {len(filesDict)-failed_count}/{len(filesDict)}
        """)
    ) 
    outcome_print_group = Group(
            table,
            f"{messenge}" if result_reverted else '',
            f"\nTotal time taken: {round(time_elasped, 2)} seconds",
    )
    print(Panel(outcome_print_group, subtitle="Compression Completed", border_style="bright_green", expand=False))
    

def designate_preserve_saveFolder(targetDict: dict):
    import datetime
    folder_path = os.path.join(CURRENT_DIR, f'compressed-files-{datetime.datetime.now().strftime('%Y.%m.%d-%H.%M.%S')}')

    while True:
        try:
            os.mkdir(folder_path)
            break
        except PermissionError:
            log.error(f"Permissions Error. Cannot create folder on {CURRENT_DIR}")
            folder_path = input("Please redesignate --preserve folder.\n> ")
            log.error("Error. Folder already exists.")
        except IOError:
            if os.path.exists(folder_path):
                log.error("Path already exists. Please designate new folder.")
                folder_path = input("> ")
            else:
                log.error("IOError while creating directory. Program terminated.")
                raise PrettyErrorDisplay("IOError issue.")
    for file_entry in targetDict.items():
        file_entry[1]['saving_path'] = os.path.join(folder_path, os.path.basename(file_entry[0]))
    
    return targetDict



def pymupdf_multiprocess_childTask(task_details: tuple):
    file_entry, pymupdf_settings, tempPath = task_details

    target = file_entry[0]
    target_properties = file_entry[1]

    try:
        with pymupdf.open(target) as doc:
            # temp files created to solve incremental saving issue
            if (os.path.getsize(target) >= 157286400): log.info(f"Active compressing file too large (>150mb). May take a while. File: {target}") # 150mb in bytes
            
            doc.save(tempPath, garbage=pymupdf_settings["garbageStrength"], deflate=True, deflate_fonts=True, deflate_images=True)
            target_properties['final_size'] = os.path.getsize(tempPath)
            
            if (target_properties['initial_size'] <= target_properties['final_size']):
                log.warning(f"File uncompressed. Resulted file not smaller than original. File: [purple]{return_basename(target)}[/purple]")
                os.remove(tempPath)
                target_properties['valid'] = False
                target_properties['state'] = 'Unchanged'
            else:
                target_properties['valid'] = True
                target_properties['state'] = "Compressed"

                log.info(f"File Compressed: {target}")
        
                if target == target_properties['saving_path']: 
                    os.replace(tempPath, target)

    except Exception as e: 
        log.error(text_dedent(f"""
        --------------------
        CAUTION. '{return_basename(target)}' cannot be compressed
        Error type: {e}
        --------------------
        """))
        target_properties['valid'] = False
        target_properties['state'] = 'PyMuPDF failure'

    return file_entry, tempPath


def pymupdf_compression(filesDict: dict, pymupdf_settings):

    from rich.progress import (
        Progress, BarColumn, TaskProgressColumn, TextColumn,
        TimeElapsedColumn, MofNCompleteColumn
    )
    from multiprocessing import Pool
    
    main_columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ]

    # stores the target file properties, pymupdf settings for compression and temp file
    worker_tasks_details = []
    # stores active temp files. After compress, these temp files are removed. If any temp file remained,
    # program needs to delete them
    temp_paths = []

    for file_entry in filesDict.items():
        target = file_entry[0]
        target_savingPath = file_entry[1]['saving_path']
        temp = (target + ".temp") if target == target_savingPath else target_savingPath
        worker_tasks_details.append((file_entry, pymupdf_settings, temp))
        temp_paths.append(temp)

    log.info("Started PyMuPDF compression runtime.")

    with Progress(*main_columns, transient=True) as progress:
        pool = Pool(processes=4, initializer=initialize_pymupdf)
        runtime = progress.add_task(description="PyMuPDF is running...", total=len(filesDict))

        try:
            for result in pool.imap_unordered(pymupdf_multiprocess_childTask, worker_tasks_details, chunksize=1):
                (target, target_info), tempFile = result
                temp_paths.remove(tempFile)
                filesDict[target].update(target_info) # update dict of target status after compress
                progress.update(runtime, advance=1)
            pool.close()

        except KeyboardInterrupt:
            print("[red]Aborting...[/red]")
            pool.terminate()
            # if one goes bad, every process goes bad. delete all ongoing process's temp files
        finally:
            progress.stop()
            pool.join()
            for temp in temp_paths:
                if os.path.exists(temp):
                    os.remove(temp)
                    print("Incomplete output file deleted. " + temp)
        
    return filesDict


def worker_gs_compression(task_details: tuple):
    file_entry, gs_settings, tempPath = task_details

    global subprocess
    assert subprocess is not None

    target = file_entry[0]
    target_properties = file_entry[1]
    
    if (os.path.getsize(target) >= 157286400): log.info(f"Active compressing file too large (>150mb). May take a while. File: {target}") # 150mb in bytes
    target_basename = return_basename(target)
    command = [
            gs_settings['gs_name'],
            '-sDEVICE=pdfwrite',
            f'-dCompatibilityLevel={gs_settings['compatibility']}',
            f'-dEmbedAllFonts={gs_settings['embedAllFonts']}',
            f'-dColorConversionStrategy=/{gs_settings['colorConversion']}',
            f'-dDownsampleColorImages={gs_settings['enableColorSampling']}',
            f'-dColorImageResolution={gs_settings['colorResValue']}',
            f'-dColorImageDownsampleType=/{gs_settings['colorSample']}',
            f'-dDownsampleGrayImages={gs_settings['enableGreySampling']}',
            f'-dGrayImageResolution={gs_settings['greyResValue']}',
            f'-dGrayImageDownsampleType=/{gs_settings['greySample']}',
            f'-dPDFSettings=/{gs_settings['presets']}',
            '-dNOPAUSE',
            '-dQuiet',
            '-dBATCH',
            '-dSAFER',
            f'-sOutputFile={tempPath}',
            target
        ]

    if gs_settings['custom']: command[2:2] = gs_settings['custom'].split()

    try:
        subprocess.run(command, check=True, capture_output=True)
        file_entry[1]['final_size'] = os.path.getsize(tempPath)

        if file_entry[1]['initial_size'] <= file_entry[1]['final_size']:
            log.warning(f"File uncompressed. Resulted file not smaller than original. File: [purple]{target_basename}[purple]")
            file_entry[1]['valid'] = False
            file_entry[1]['state'] = 'Unchanged'
            os.remove(tempPath)
        else:
            # only works if --preserve is not enabled.
            if target == target_properties['saving_path']:
                os.replace(tempPath, target)
            log.info(f"File Compressed: {target}")
            file_entry[1]['valid'] = True
            file_entry[1]['state'] = "Compressed"

            
    except subprocess.CalledProcessError as e:
        # two types of errors can occur here. either the file got removed during operation or ghostscript failed to run.
        # if file removed during operation, script will still continue
        file_entry[1]['valid'] = False
        os.remove(tempPath)
        log.error(f"Unable to compress file: {target_basename}")

        # what is this??
        if not os.path.exists(target):
            log.error(f"Filepath: {return_basename(target)}. File not found.")
            file_entry[1]['state'] = 'File not found.'
        else:
            file_entry[1]['state'] = '-gs failure'

    return file_entry, tempPath


def gs_compression(filesDict: dict, gs_settings):
    from pdfsimuti.utils import return_joined_filePath
    from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn ,TimeElapsedColumn

    from multiprocessing import Pool

    columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ]

    worker_tasks_details = []
    temp_paths = []

    # special warning in case colorConversion is changed
    if gs_settings["colorConversion"] != "LeaveColorUnchanged":
        from rich.prompt import Confirm
        if not Confirm.ask(f"[bold white on red]WARNING![/bold white on red] Color Conversion not default. Colors will be affected. Proceed?"):
            raise PrettyErrorDisplay("Program terminated for safety.")

    for file_entry in filesDict.items():
        target = file_entry[0] 
        target_basename = return_basename(target)
        target_savingpath = file_entry[1]['saving_path']
        tempFile = return_joined_filePath(return_dirname(target), "temp"+target_basename) if target == target_savingpath else target_savingpath
        worker_tasks_details.append((file_entry, gs_settings, tempFile))
        temp_paths.append(tempFile)

    with Progress(
        *columns, 
        transient=True) as progress:
        
        runtime = progress.add_task(description="GhostScript is running...", total=len(filesDict))
        log.info("Started GhostScript calling.")
        pool = Pool(processes=4, initializer=initialize_gs)
    
        try:
            for result in pool.imap_unordered(worker_gs_compression, worker_tasks_details, chunksize=1):
                (target, target_info), tempFile = result
                temp_paths.remove(tempFile)
                filesDict[target].update(target_info)
                progress.update(runtime, advance=1)      

        except KeyboardInterrupt:
            print("[red]Aborting...[/red]")
            raise
            
        except Exception as e:
            raise PrettyErrorDisplay(f"GhostScript compression has failed\n{e}")

        finally:
            progress.stop()
            pool.terminate()
            pool.join()
            for tempFile in temp_paths:
                if os.path.exists(tempFile):
                    os.remove(tempFile)
                    print("Incomplete output file deleted. " + tempFile)
    
    return filesDict
            

def compress_runtime(fileList: list[str] | None, source, mimecheck: bool, exclude: list, excludeSource,  compressSettings, preserve_choice):
    """
    Control the entire PDF compression process, including validation, user confirmation, runtime execution, and displaying results.
    The function measures and compares file sizes before and after compression to report the outcome and time elapsed.

    Args:
        fileList (list): A list of file or directory paths to be processed.
        mimecheck (bool): Boolean flag to enable/disable external MIME type validation.
        exclude (list): A list of file paths to exclude from compression.
        compressSettings (instance): An instance of either ``gs_settings`` or ``pymupdf_settings``.
    
    """
    from pdfsimuti.utils import validate_pdf_dict, return_confirm

    log.info("Validating files...")
    filesDict = validate_pdf_dict(fileList, source,  exclude, excludeSource,  mimecheck)

    log.info("Validation complete")
    
    # Display overview before confirm
    display_overview_confirm(filesDict, compressSettings, preserve_choice)


    if return_confirm("\nDo you want to continue with this settings?"):
        import time
        
        validated_pdf_dict = {file_entry: file_properties for file_entry, file_properties in (filesDict or {}).items() if file_properties['valid'] != False}

        # 1st size capture: Initial Runtime
        start_time = time.time()
        log.info("Compression runtime started.")

        # if preserve is enabled, the save files are changed. if not, they are same value as target which meant overwrite.
        if preserve_choice: 
            filesDict = designate_preserve_saveFolder(validated_pdf_dict)

        #########################################
        match compressSettings.__class__.__name__:
            case 'gs_settings': filesDict = gs_compression(validated_pdf_dict, compressSettings)
            case 'pymupdf_settings': filesDict = pymupdf_compression(validated_pdf_dict, compressSettings)
        #########################################
        log.info("Compression runtime over.")
        
        # 2nd Size Capture: Concluding Runtime
        end_time = time.time()

        # Display compress outcome.
        display_compress_outcome(validated_pdf_dict, float(end_time-start_time))
    else:
        print("[red]Aborted[/red]")


def compress(
    items: Annotated[Optional[List[str]], typer.Argument(help="PDF file(s) to be compressed. Can be single or multiple.", metavar="pdf_item")] = None,
    mimecheck: Annotated[bool, typer.Option(help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[List[str], typer.Option("--exclude", "-x", help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional options")]=[],
    source: Annotated[str, typer.Option(help="Add files as filepaths from external files (.txt)", rich_help_panel="Additional options", metavar=".txt FILE")] = '',
    excludeSource: Annotated[str, typer.Option(help="Specify external file as exclude filepath source", rich_help_panel="Additional options", metavar=".txt FILE")] = '',
    
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
    from pdfsimuti.utils import rtn_gs_name
    commandline_gs_exception = ["-p", '--presets', "--gs_custom", "--compatibility", "-cs", "-gs",  "--color-res", "--color_sample_type", "--color-down", "--grey-res", "--grey_down", "--grey_sample_type"]
    compressSettings = None

    if any(value in commandline_gs_exception for value in sys.argv) and compressMethod == "pymupdf":
        raise PrettyErrorDisplay("Ghostscript options cannot be added to PyMupdf compression mode.")
    
    elif compressMethod == ("gs" or "ghostscript"):
        compressSettings = gs_settings(rtn_gs_name(), compatibility.value, presets.value,  embedFonts, color_down, color_res, color_sample_type, gray_down, grey_Res, grey_sample_type, colorConversion.value ,gs_custom)
    
    elif compressMethod == "pymupdf":
        compressSettings = pymupdf_settings(garbageStrength=garbage)
    
    if items == None and not source:
        raise PrettyErrorDisplay("No filepaths were added to compress.py or with --source")

    # compress runtime handles the main load
    compress_runtime(items, source, mimecheck, exclude, excludeSource, compressSettings, preserve_choice=preserve)
