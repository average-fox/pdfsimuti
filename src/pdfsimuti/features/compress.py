import typer
import os

from typing import List, Annotated, Optional, Literal
from enum import Enum
from pathlib import Path

from rich import print
from rich.table import Table
from rich.panel import Panel
from rich.console import Group

from pdfsimuti.utils import CURRENT_DIR
from pdfsimuti.utils import PrettyErrorDisplay, text_dedent, typeFileDict

from collections.abc import Callable
from dataclasses import dataclass

app = typer.Typer(add_completion=False, suggest_commands = True, rich_markup_mode = "rich", pretty_exceptions_show_locals=False)
pymupdf = None
subprocess = None

from pdfsimuti.logClass import Log, console

log = Log(console).logger

# for annotations only
type typeLogRes = tuple[Literal['warning','info','error',''],str]
type typeWorkerResults = tuple[
    tuple[Path, typeFileDict],
    Path,
    typeLogRes
]
type typeGSPresets = Literal['ebook', 'screen', 'printer', 'prepress']
type typeGSSampleControl = Literal['subsample', 'average', 'bicubic']
type typeGSColorControl = Literal['LeaveColorUnchanged', 'Gray', 'RGB', 'CMYK']


@dataclass
class pymupdfGarbageControl:
    max:int = 4
    min:int = 0


class compressMethodChoice(str, Enum):
    gs = "gs"
    pymupdf = "pymupdf"
    ghostscript = "ghostscript"


class gsColorConversionStrategy(str, Enum):
    """
    GhostScript conversion Strategy choices.
    """
    leaveColorUnchanged="LeaveColorUnchanged"
    Gray="Gray"
    RGB="RGB"
    CMYK="CMYK"


class gsCompatibilityChoice(str, Enum):
    """
    GhostScript compatibility settings.
    """
    one_three = "1.3"
    one_four = "1.4"
    one_seven = "1.7"
    two_zero = "2.0"


class gsPDFshrinkPresets(str, Enum):
    """
    GhostScript shrinking presets.
    """
    ebook = "ebook"
    screen = "screen"
    printer = "printer"
    prepress = "prepress"


class gsDownSampleControl(str, Enum):
    """
    GhostScript color/grey downgrading sample control.
    """    
    subsample = "subsample"
    average = "average"
    bicubic = "bicubic"


class gs_settings:
    def __init__(self, 
                 gs_name:str, compatibility:float, presets:Literal['ebook', 'screen', 'printer', 'prepress'], embedAllFonts:bool, colorConversion:typeGSColorControl,  
                 enableColorSampling:bool ,colorResValue:int, colorSample:typeGSSampleControl, enableGreySampling:bool, greyResValue:int, 
                 greySample:typeGSSampleControl, custom:str):
        self.gs_name = gs_name

        self.compatibility = compatibility
        self.presets = presets
        self.embedAllFonts = str(embedAllFonts).lower()
        self.colorConversion = colorConversion

        self.enableColorSampling = str(enableColorSampling).lower() # color_down
        self.colorResValue = colorResValue # color_res
        self.colorSample = colorSample.capitalize() # color_sample_type

        self.enableGreySampling = str(enableGreySampling).lower() # gray_down
        self.greyResValue = greyResValue # gray_res
        self.greySample = greySample.capitalize()  # grey_sample_type

        # process custom commands
        self.custom = custom
        self.validate_gs_commands()
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def validate_gs_commands(self):
        log.info("Validating gs commands..")
        import re
        if self.custom and (match := re.search(r"dColorConversionStrategy=([^\s-]+)",self.custom)): self.colorConversion = match.group(1)
        if self.colorConversion != "LeaveColorUnchanged":
                from pdfsimuti.utils import return_confirm
                log.warning("Color Conversion not default. Colors will be affected.")
                if not return_confirm("Proceed?", default=False):
                    raise PrettyErrorDisplay("Program terminated for safety.")
                
        # below statement not tested
        if re.search(r'\b\w+\.pdf\b',self.custom): #locate all occurance of "pdf files"
            # GhostScript is complicated. Having external files via ghostscript is hazard. External files can only be added outside gs_custom
            # if this feature is needed, open up an issue to fix the problem.
            log.error("Invalid command found")
            raise PrettyErrorDisplay(f"""
                Ghostscript via PDFsimuti cannot have external PDF files. Please insert them outside of --gs-custom.
                Custom -gs command detected: '{self.custom}'  
            """)
    

    def display_properties(self, preserve_choice:bool):
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

    def initialize_worker(self):
        import signal
        signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore worker's warnings

        import subprocess as sp
        global subprocess

        if subprocess is None: subprocess = sp


class pymupdf_settings:
    def __init__(self, garbageStrength:Annotated[int, pymupdfGarbageControl]):
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

    def initialize_worker(self):
        import signal
        signal.signal(signal.SIGINT, signal.SIG_IGN) # ignore worker's warnings

        global pymupdf
        if pymupdf is None:
            import pymupdf as _pymupdf
            pymupdf = _pymupdf


def display_overview_confirm(filesDict, compressSettings, preserve_choice):
    """
    Display a summary table of files to be compressed and the current compression settings, 
    then prompt the user for final confirmation to proceed.

    Args:
        filesDict (dict): A dictionary of validated file paths ready for compression.
        compressSettings (instance): An instance of either ``gs_settings`` or ``pymupdf_settings``.
        preserve_choice (bool): Confirm if `--preserve` got passed or not.
    """    
    from rich.rule import Rule
    from pdfsimuti.utils import returnValidDisplayRenderable

    panel_group = Group(
        Rule("Compress Settings"),
        console.render_str(f"{compressSettings.display_properties(preserve_choice)}"),
        Rule("Selected files for Compression"),
        returnValidDisplayRenderable(filesDict)
    )
    console.print(Panel(panel_group, subtitle="Compress Overview", border_style="bright_cyan", expand=False))


def display_compress_outcome(filesDict : dict, time_elasped: float):
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
        target = file_entry[1]['savingPath']

        if not file_entry[1]['valid']:
            failed_count += 1
            if file_entry[1]['state'] == "[yellow]Unchanged[/yellow]":
                result_reverted = True
            table.add_row(f"{index}", f"{target.name}", f"{target}", str(round(initial_size,3))+ " MB", "[red]Error[/red]", f"{file_entry[1]['state']}")
        else:
            compression_calculate = abs(round((initial_size - final_size)/initial_size*100, 5))
            table.add_row(f"{index}", target.name, f"{target}", f"{round(initial_size,3)} MB", f"{round(final_size,3)} MB", f'[green]{"-"+compression_calculate}%[/green]' if initial_size > final_size else f'[red]{"+"+compression_calculate}%[/red]')


    messenge = (
        text_dedent(f"""
        [yellow]CAUTION![/yellow] Some files were not compressed. Unchanged files are not affected
        If preserve mode is active, this files are not copied.
        Total Processed: {len(filesDict)-failed_count}/{len(filesDict)}
        """)
    ) 
    outcome_print_group = Group(
            table,
            f"{messenge}" if result_reverted else '',
            f"\nTotal time taken: {str(round(time_elasped, 2))} seconds",
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



def worker_pymupdf_compression(task_details: tuple[tuple[Path, typeFileDict], pymupdf_settings | gs_settings, Path]) -> typeWorkerResults:

    file_entry, pymupdf_settings, tempPath = task_details

    global pymupdf
    assert pymupdf is not None

    target = file_entry[0]
    target_properties = file_entry[1]
    log_response:tuple[str, str] = ("", "")

    try:
        with pymupdf.open(target) as doc:
            doc.save(tempPath, garbage=pymupdf_settings["garbageStrength"], deflate=True, deflate_fonts=True, deflate_images=True)
            target_properties['final_size'] = os.path.getsize(tempPath)
            
            if (target_properties['initial_size'] <= target_properties['final_size']):
                log_response = ("warning", f"File unchanged. File: {target}")
                os.remove(tempPath)
                target_properties['valid'] = False
                target_properties['state'] = '[yellow]Unchanged[/yellow]'
            else:
                target_properties['valid'] = True
                target_properties['state'] = "[green]Compressed[/green]"

                log_response = ("info", f"File compressed: {target}")
        
                if target == target_properties['savingPath']: 
                    os.replace(tempPath, target)

    except Exception as e: 
        log_response = ("error", text_dedent(f"""
        --------------------
        CAUTION. '{target.name}' cannot be compressed.
        Error message: {e}
        Error type: {e.__class__.__name__}
        --------------------
        """))
        target_properties['valid'] = False
        target_properties['state'] = '[red]PyMuPDF failure[/red]'

    return file_entry, tempPath, log_response


def worker_gs_compression(task_details: tuple[tuple[Path, typeFileDict], pymupdf_settings | gs_settings, Path]) -> typeWorkerResults:
    # TODO: fix the annot. here

    file_entry, gs_settings, tempPath = task_details

    global subprocess
    assert subprocess is not None

    target = file_entry[0]
    target_properties = file_entry[1]
    log_response:typeLogRes = ('','')

    command = [
            gs_settings['gs_name'],
            '-sDEVICE=pdfwrite',
            f'-dPDFSettings=/{gs_settings['presets']}',
            f'-dCompatibilityLevel={gs_settings['compatibility']}',
            f'-dEmbedAllFonts={gs_settings['embedAllFonts']}',
            f'-dColorConversionStrategy=/{gs_settings['colorConversion']}',
            f'-dDownsampleColorImages={gs_settings['enableColorSampling']}',
            f'-dColorImageResolution={gs_settings['colorResValue']}',
            f'-dColorImageDownsampleType=/{gs_settings['colorSample']}',
            f'-dDownsampleGrayImages={gs_settings['enableGreySampling']}',
            f'-dGrayImageResolution={gs_settings['greyResValue']}',
            f'-dGrayImageDownsampleType=/{gs_settings['greySample']}',
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
            log_response = ("warning", f"File [yellow]unchanged[/yellow]. File: {target}")
            file_entry[1]['valid'] = False
            file_entry[1]['state'] = '[yellow]Unchanged[/yellow]'
            os.remove(tempPath)
        else:
            # only works if --preserve is not enabled.
            if target == target_properties['savingPath']:
                os.replace(tempPath, target)

            log_response = ("info", f"File [green]compressed[/green]: {target}")
            file_entry[1]['valid'] = True
            file_entry[1]['state'] = "[green]Compressed[/green]"

            
    except subprocess.CalledProcessError:
        file_entry[1]['valid'] = False
        os.remove(tempPath)
        log_response = ("error", f"Unable to compress file: [red]{target}[/red]")

        # what is this??
        if not os.path.exists(target):
            log_response = ("error", f"Filepath: [red]{target.name}[/red]. File not found.")
            file_entry[1]['state'] = 'File not found.'
        else:
            file_entry[1]['state'] = '[red]-gs failure[/red]'

    return file_entry, tempPath, log_response


def compress_engine(
        compressMode:Literal["GhostScript","PyMuPDF"], 
        compressSettings:pymupdf_settings|gs_settings, 
        compressWorker:Callable[[tuple
            [
            tuple[Path, typeFileDict], pymupdf_settings | gs_settings, Path]], 
            typeWorkerResults,
            ], 
        filesDict:dict[Path, typeFileDict]
    ):
    """
    handles the process of compressing the files by tasking it to it's respective workers.
    """

    from multiprocessing import Pool
    from rich.progress import Progress, BarColumn, TaskProgressColumn, TextColumn, TimeElapsedColumn, MofNCompleteColumn

    progress_column = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ]

    worker_task_details = []
    temp_paths = []

    for file_entry in filesDict.items():
        target = file_entry[0]
        targetSavePath  = file_entry[1]["savingPath"]
        tempFile = Path(target).with_suffix(".pdf.temp") if target == targetSavePath else targetSavePath
        worker_task_details.append((file_entry, compressSettings, tempFile))
        temp_paths.append(tempFile)

    log.info(f"Started {compressMode} compression runtime.")

    with Progress(*progress_column, transient=True, console=console) as progress:
        runtime = progress.add_task(description=f"{compressMode} is running...", total=len(filesDict))
        pool = Pool(processes=4, initializer=compressSettings.initialize_worker)

        try:
            for result in pool.imap_unordered(compressWorker, worker_task_details, chunksize=1):
                (target, target_info), tempFile, outcome= result
                temp_paths.remove(tempFile)
                filesDict[target].update(target_info) # update dict of target status after compress
                level, message = outcome
                getattr(log, level)(message)
    
                progress.update(runtime, advance=1)
            pool.close()

        except KeyboardInterrupt:
            print("[red]Aborting...[/red]")
            pool.terminate()

        except Exception as e:
            pool.terminate()
            raise PrettyErrorDisplay(f"Compression ({compressMode}) has failed\n{e}")


        finally:
            progress.stop()
            pool.join()
            for temp in temp_paths:
                if os.path.exists(temp):
                    os.remove(temp)
                    log.debug("Incomplete output file deleted. " + str(temp))

            for _, file_property in filesDict.items():
                if file_property["state"] == None:
                    file_property["state"] = "[red]Incomplete[/red]"
                    file_property["valid"] = False
        
    return filesDict


def compress_runtime(fileList: list[Path]|None, source: list[Path]|None, mimecheck: bool, exclude: list[Path]|None, excludeSource: list[Path]|None,  compressSettings, preserve_choice:bool):
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
            case 'pymupdf_settings': filesDict = compress_engine("PyMuPDF", compressSettings, worker_pymupdf_compression, validated_pdf_dict)
            case 'gs_settings': filesDict = compress_engine("GhostScript", compressSettings, worker_gs_compression, validated_pdf_dict)
        #########################################
        log.info("Compression runtime complete.")
        
        # 2nd Size Capture: Concluding Runtime
        end_time = time.time()

        # Display compress outcome.
        display_compress_outcome(validated_pdf_dict, float(end_time-start_time))
    else:
        print("[red]Aborted[/red]")

@app.command(
    help="""
    Compress PDF(s) into smaller sizes.

    _______ _______ __   __ _______ ______   _______ _______ _______ 
    |       |       |  |_|  |       |    _ | |       |       |       |
    |   ----|   _   |       |    _  |   | || |    ___|  _____|  _____|
    |  |    |  | |  |       |   |_| |   |_||_|   |___| |_____| |_____ 
    |  |    |  |_|  |       |    ___|    __  |    ___|_____  |_____  |
    |  |____|       | ||_|| |   |   |   |  | |   |___ _____| |_____| |
    |_______|_______|_|   |_|___|   |___|  |_|_______|_______|_______|
    
    """)

    # note. Optional from typing for Optional[List[type]] is the same as List[type] | None
def compress(
    items: Annotated[Optional[List[Path]], typer.Argument(help="PDF file(s) to be compressed. Can be single or multiple.", metavar="PDF file")] = None,
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF mimecheck for advanced PDF validation")]=True,
    exclude: Annotated[Optional[List[Path]], typer.Option("--exclude", "-e", help="Specify file to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional options")]=None,
    source: Annotated[Optional[List[Path]], typer.Option("--source", "-s", help="Add files as filepaths from external files (.txt)", rich_help_panel="Additional options", metavar=".txt FILE")] = None,
    excludeSource: Annotated[Optional[List[Path]], typer.Option("--exclude-source", "-es", help="Specify external file as exclude filepath source", rich_help_panel="Additional options", metavar=".txt FILE")] = None,
    compressMethod: Annotated[compressMethodChoice, typer.Option("-cm", "--compressMethod", help="Compression application choice. Tip: 'ghostscript' can be written as 'gs'", rich_help_panel="Additional options", metavar="[gs/ghostscript|pymupdf]")] = compressMethodChoice.pymupdf,
    preserve: Annotated[bool, typer.Option(help="Preserve file on compress. Will be saved in a folder on the working directory.", rich_help_panel='Additional options')]=False,

    garbage: Annotated[int, typer.Option("--garbage", "-g", max=4, min=0, help="PyMuPDF garbage strength control", rich_help_panel="PyMuPDF Settings")] = 4,

    compatibility: Annotated[gsCompatibilityChoice, typer.Option(help="Specify ghostscript compatibility mode", rich_help_panel="GhostScript options")] = gsCompatibilityChoice.one_seven,
    presets: Annotated[gsPDFshrinkPresets, typer.Option("--preset", help="Specify ghostscript pdf compression presets", rich_help_panel="GhostScript options")] = gsPDFshrinkPresets.ebook,
    embedAllFonts: Annotated[bool, typer.Option("--embed-all-fonts/--no-embed-all-fonts",help="Embed fonts in PDF for cross-platform font support", rich_help_panel="GhostScript options")] = True,
    colorConversion: Annotated[gsColorConversionStrategy, typer.Option("-cc", "--color-conversion", help="[red](Caution!)[/red] Change color space of the document.", case_sensitive=False, rich_help_panel="GhostScript options")] = gsColorConversionStrategy.leaveColorUnchanged,
    
    color_down:Annotated[bool, typer.Option("--color-down/--no-color-down", help="Enable reduction of color images", rich_help_panel="GhostScript options (Color Down Sampling)")] = True,
    color_res: Annotated[int, typer.Option("--color-res", min=0, help="Target DPI for color image resolution. Low DPI = More pixalated", rich_help_panel="GhostScript options (Color Down Sampling)")] = 150,
    color_sample_type: Annotated[gsDownSampleControl, typer.Option("--color-sample-type", "-cst", help="Specify algorithm for downsampling", rich_help_panel="GhostScript options (Color Down Sampling)")] = gsDownSampleControl.bicubic,
    
    grey_down: Annotated[bool, typer.Option("--grey-down/--no-grey-down", help="Enable reduction of Black/White", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = True,
    grey_res: Annotated[int, typer.Option("--grey-res", min=0, help="Target DPI for grey image resolution. Low DPI = More pixalated", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = 150,
    grey_sample_type: Annotated[gsDownSampleControl, typer.Option("--grey-sample-type", "-gst", help="Specify algorithm for downsampling", rich_help_panel="GhostScript options (Grey Image Down Sampling)")] = gsDownSampleControl.bicubic,
    
    gs_custom: Annotated[str, typer.Option('--gs-custom', help="Custom commands for ghostscript. Commands must be case-sensitive. Can override everything.", rich_help_panel="GhostScript options (Advanced)")] = ''
    ):

    log.info("Performing command line validation")
    
    import sys # detect for ghostscript commands.
    
    
    commandline_gs_exception = [
        '--compatibility', "--preset", "--embed-all-fonts", "--no-embed-all-fonts", "-cc", 
        "--color-conversion",  "--color-down", "--no-color-down", "--color-res", "--color-sample-type", "-cst", 
        "--grey-down", "--no-grey-down","--grey-res", "--grey-sample-type", "-gst", "--gs-custom"]
    commandline_pymupdf_exception = [
        '--garbage', '-g'
    ]

    compressSettings:gs_settings | pymupdf_settings | None = None

    if items == None and not source:
        raise PrettyErrorDisplay("No filepaths were added to compress.py or with --source")
    
    if any(value in commandline_gs_exception for value in sys.argv) and compressMethod == "pymupdf":
        raise PrettyErrorDisplay("Ghostscript options cannot be added to PyMuPDF.")

    elif any(value in commandline_pymupdf_exception for value in sys.argv) and compressMethod == "gs":
        raise PrettyErrorDisplay("PyMuPDF options cannot be added to GhostScript.")

    elif compressMethod in ("gs","ghostscript"):
        from pdfsimuti.utils import get_gs_name
        from pdfsimuti.diagnostic.checkhealth import check_gs_installation

        if not check_gs_installation(gs_name=get_gs_name()):
            raise PrettyErrorDisplay("""
            Unable to proceed. GhostScript is not installed on your system.
            
            Recommend either installing GhostScript or switching to default. 
            """)
        compressSettings = gs_settings(get_gs_name(), float(compatibility.value), presets.value, embedAllFonts, colorConversion.value, color_down, color_res, color_sample_type.value, grey_down, grey_res, grey_sample_type.value, gs_custom)
    
    elif compressMethod == "pymupdf":
        compressSettings = pymupdf_settings(garbageStrength=garbage)

    # compress runtime handles the main load
    compress_runtime(items, source, mimecheck, exclude, excludeSource, compressSettings, preserve_choice=preserve)
