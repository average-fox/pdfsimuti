import pymupdf
import os
import re

from typing import List, Optional, Annotated
from enum import Enum
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from rich import print

from pdfsimuti.utils import validate_pdf_dict, exit_program, return_confirm
from pdfsimuti.utils import PrettyErrorDisplay, DEFAULT_OUTPUT, typeFileDict, OPER_SYS
from rich.console import Group, Console, RenderableType

console = Console()
import typer
app = typer.Typer(add_completion=False, suggest_commands = True, rich_markup_mode = "rich", pretty_exceptions_show_locals=False)

from pdfsimuti.logClass import Log, console
log = Log(console).logger

type typeFilesDict = dict[Path, typeFileDict] | None

class SortOrder(str, Enum):
    none = "none"
    normal = "normal"
    reverse = "reverse"
    modified = "modified"
    creation = "creation"

    def __str__(self):  
        return self.name.replace("_", " ").capitalize() # Get the name of the class value for overview
    
    def description(self):
        description = { 
            SortOrder.none : "Files are arranged as user added.",
            SortOrder.normal : "Files are arranged alphabetically.",
            SortOrder.reverse : "Files are arranged alphabetically reversed.",
            SortOrder.modified : "Files are arranged based on their modified dates.",
            SortOrder.creation : "Files are arranged based on their creation dates."
        }
        return description.get(self)


def sort_natural(files_dict: dict[Path, typeFileDict], reverse=False) -> dict[Path, typeFileDict]:
    from itertools import islice

    def nat(item):
        return [
            int(item) if item.isdigit() else item.lower() for item in re.split(r'(\d+)', item) # turns a string into letters and digits
        ]

    
    nonwhitespace = [(position, item.name.replace(" ", "")) for position, item in enumerate(files_dict, start=0)]
    val_sort = [item[0] for item in sorted(nonwhitespace, key=lambda item: nat(item[1]), reverse=reverse)]

    result = {}
    for index in val_sort:
        entry, value = next(islice(files_dict.items(), index, None))
        result[entry] = value

    return result


def sort_dict(sort_type:str, files_dict) -> dict[Path, typeFileDict] | None:


    match sort_type:
        case 'none':
            return files_dict
        case 'normal':
            return sort_natural(files_dict)
        case 'reverse':
            return sort_natural(files_dict, reverse=True)
        case 'modified':
            return dict(sorted(files_dict.items(), key=lambda item: os.path.getmtime(item[0])))
        case 'creation':
            return dict(sorted(files_dict.items(), key=lambda item: os.path.getctime(item[0])))


def check_pure_dict(filesDict: dict[Path, typeFileDict]) -> bool:
    for file_item in filesDict.items():
        target_validity = file_item[1]['valid']
        if not target_validity: return False
    return True


def reserved_filenaming_charCheck(filename:str) -> bool:
    if re.search(r'[\"#$|<>:?*/(\)\\\"]', filename):
        return True
    return False


def designate_saving_filePath(target: str) -> str: 

    savePath = Path(DEFAULT_OUTPUT) if target == "" else Path(target)
    folder_creation = False
    warned = False
    overwrite = False

    while Path(savePath):
        match Path(savePath):

            # if the user gives a filename like filename<>.pdf then it is an automatic False according to return_confirm()
            case subject if (not subject.resolve().is_relative_to("/home")) and OPER_SYS == "linux" and not warned:
                print("\n[red]WARNING[/red]. Selected output filepath not from /home (Possibly a Linux Root FHS). \nAbort immediately if you don't know what you're doing.")
                warned = return_confirm(caution=True, default=True)
                if not warned: 
                    savePath = Path(typer.prompt("Enter output filepath again: "))

            case subject if subject.is_dir():
                print("\n[yellow]INVALID[/yellow] Given value is a path. Include filename as well.")
                savePath = Path(typer.prompt("Enter output filepath again: "))

            case subject if subject.suffix != ".pdf" or str(savePath) == "pdf":
                savePath = Path(str(savePath) + ".pdf")
                continue

            case subject if reserved_filenaming_charCheck(str(subject.name)):
                print("\n[yellow]INVALID[/yellow] Specfied output file has forbidden Windows NTFS characters.")
                print("[yellow]ADVICE[/yellow] Change your filename to make it cross platform compatible.")
                if return_confirm("Change your filename?", caution=True):
                    subject = subject.with_name(typer.prompt("Enter new filename only: "))

            case subject if subject.exists() and not overwrite:
                print("\n[red]Error![/red] Specified output filepath already exists.")
                if not return_confirm("Do you wish to overwrite this file? (Default: Y)"):    
                    print("\nFilename cannot be same if overwrite isn't allowed")
                    savePath = Path(typer.prompt("Enter new output path or filename again: "))
                else: overwrite = True

            case subject if not (parent := subject.parent).exists() and not folder_creation:
                print(f"\n[red]Error![/red] File directory doesn't exist: [purple]{parent}[/purple]")
                folder_creation = return_confirm("Create new directory?")
                if not folder_creation:
                    savePath = Path(typer.prompt("Enter new output path or filename again: "))
            case _:
                break

    return str(savePath)


def return_merge_success_display(outputPath:Path) -> RenderableType:
    outcome_table = Table(show_header=False, expand=False, show_lines=True)
    outcome_table.add_row("[u][b]Filename[/b][/u]", outputPath.name)
    outcome_table.add_row("[u][b]Folder[/b][/u]", str(Path.cwd()) if outputPath.parent.absolute() == Path.cwd() else str(outputPath.parent.absolute()))
    outcome_table.add_row("[u][b]Absolute Path[/b][/u]", str(outputPath.absolute()))

    return outcome_table
    


def display_merge_overview(filesDict:dict[Path, typeFileDict], outputPath:Path, preserveFiles: bool, sort:str) -> RenderableType:

    from rich.rule import Rule
    from pdfsimuti.utils import returnValidDisplayRenderable # display file status despite the result

    fileSize = 0
    merge_table_details = Table(show_header=False, show_lines=True, highlight=True, expand=True)

    # Calculate estimated size of the merge
    for item in filesDict: fileSize += Path(item).stat().st_size / (1024 * 1024)
    merge_table_details.add_row("[underline bold]Output file[/underline bold]:" , f'{"[yellow italic](Overwriting)[/yellow italic] " if outputPath.exists() else ""}' + f"{outputPath.name}")
    merge_table_details.add_row("[underline bold]Saving directory[/underline bold]:", f'{"[yellow italic](Overwriting)[/yellow italic] " if outputPath.exists() else ""}' + f"{Path.cwd() if outputPath.parent == "" else outputPath.parent.absolute()}")
    merge_table_details.add_row("[underline bold]Sort Order[/underline bold]:", f"[i]({str(sort)})[/i] {SortOrder(sort).description()}")
    merge_table_details.add_row("[underline bold]Preserve Mode[/underline bold]:", f"{"[italic green bold]Preserve ON![/italic green bold] Files will not be deleted after merging." if preserveFiles else "[italic red bold]Preserve OFF! [/italic red bold]PDF files will be deleted after merging."}")
    merge_table_details.add_row("[underline bold]Estimated Size[/underline bold]:", f">{fileSize: .2f} MB")
  
    return Group(
        Rule("Merge Order Overview"),
        returnValidDisplayRenderable(filesDict),
        Rule("Merge Settings"),
        merge_table_details,
        console.render_str(f"{"Estimated file size is big. Merge operations will take a while." if fileSize > 100 else ""}")
    )


def generate_merged_pdf(itemsDict:dict, outputFile:str, preserveFiles=True):

    log.info("Started merge operations.")
    # in case the user approves overwrite.
    # if not done, this will remove the merged file if --no-preserve is active
    with pymupdf.open() as doc:
        for item_entry in itemsDict.keys():
            doc.insert_file(item_entry)
            log.info(f'Inserted file: {item_entry}')
        log.info("Finalizing saving...")
        doc.save(outputFile)
    
    if outputFile in itemsDict:
        itemsDict.pop(outputFile)

    # only delete after merging
    if not preserveFiles:
        for item_entry in itemsDict: 
            os.remove(item_entry)

    log.info("Merge operations completed.")
        

def merge_runtime(filesDict, output:str, preserveFiles:bool, sort:str):

    output = designate_saving_filePath(output)
    output_dir = Path(output).parent
    create_directory = False
    APPROVED = False

     # display overview to the user
    console.print(Panel(display_merge_overview(filesDict, Path(output), preserveFiles, sort), border_style="blue", expand=False))
    
    if not preserveFiles:
        print("[yellow]CAUTION![/yellow] [code]--no-preserve[/code] flag present! Files will be deleted after successful merge!")
        if not return_confirm("Proceed?"):
            exit_program()

    if not check_pure_dict(filesDict):
        print("[yellow]CAUTION![/yellow] Not all files are clear for merging. They will get excluded. Continue?")
        APPROVED = True
        if not return_confirm("Proceed?"):
            exit_program()


    if not APPROVED: 
        if not return_confirm("Merge with selected documents?", default=False): exit_program()

    if not os.path.isdir(output_dir): 
        try: 
            os.makedirs(output_dir)
            create_directory = True
        except PermissionError:
            raise PrettyErrorDisplay(f"Program failed. Unable to create directory: {output_dir}")
    
    # purify dict of rejected items
    validated_dict = {key:value for key, value in filesDict.items() if value['valid'] == True or value['valid'] == None}

    try:
        generate_merged_pdf(validated_dict, output, preserveFiles)

    except KeyboardInterrupt:
        log.error("Runtime aborted.")
        if create_directory:
            log.debug("Removing created directory...")
            os.rmdir(output_dir)
            log.debug("Removed")
        exit_program("Program interrupted and exited.")

    except ValueError as e:
        raise PrettyErrorDisplay(f"""
        Fatal. PyMuPDF unable to read data.
        Exception: {e}
        """)
    
    except Exception as e:  
        raise PrettyErrorDisplay(f"""
            Program failed to run.
            Error message: {e}
            Error type: {e.__class__.__name__}
        """)

    # at this point, merge is sucessful
    # display successful merge details
    console.print(Panel(return_merge_success_display(Path(output)), subtitle="MERGE COMPLETED", border_style="green", expand=False))



@app.command(help="""
Merges several PDFs into a super PDF.

___   __ _______ ______   _______ _______ 
|  |_|  |       |    _ | |       |       |
|       |    ___|   | || |    ___|    ___|
|       |   |___|   |_||_|   | __|   |___ 
|       |    ___|    __  |   ||  |    ___|
| ||_|| |   |___|   |  | |   |_| |   |___ 
|_|   |_|_______|___|  |_|_______|_______|

- Output file is 'merged.pdf' by default but you can change it using --ouput TEXT
- Tip: Pass '.' to include current directory.
- Tip: You can pass folder paths as well just like adding PDF filenames.
"""
)

def merge(
    items: Annotated[Optional[List[Path]], typer.Argument(help="PDF files to merge. You can also use --source instead.", metavar="PDF file")]=None,
    sort: Annotated[SortOrder, typer.Option("--sort" , case_sensitive=False, help="Sort files for order-specific merging", rich_help_panel="Additional Options")] = SortOrder.none,
    exclude: Annotated[Optional[List[Path]], typer.Option("--exclude", "-e", help="Specify files to exclude from merging.", rich_help_panel="Additional Options", metavar="FILEPATH")]=None,
    source: Annotated[Optional[List[Path]], typer.Option("--source", "-s", help="Add files as filepaths from external files (.txt)", rich_help_panel="Additional options", metavar=".txt FILE")] = None,
    excludeSource: Annotated[Optional[List[Path]], typer.Option("--exclude-source", "-es", help="Specify external file as exclude filepath source", rich_help_panel="Additional options", metavar=".txt FILE")] = None,
    
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    output: Annotated[str, typer.Option("--output", "-o", help="Save output file name. Accepted formats like folder/file.pdf or file.pdf", rich_help_panel="Options")]=DEFAULT_OUTPUT):


    command_exception = ["--source" , "-s", "--exclude", "-e", "--preserve", "--no-preserve", "-p", "-np", "--exclude-source", "-es", "--sort"]

    # more testing required

    # in case someone pass --source or --exclude as --output
    if output == "--mimecheck" or output == "-m" or output == "-nm" or output =="-no-mimecheck":
        raise PrettyErrorDisplay("--mimecheck flag can't be used after --output.")
    
    if items == None and not source:
        raise PrettyErrorDisplay("No filepaths were added to merge.py or with --source")

    from pdfsimuti.main import return_pymupdf_moduleSpec
    if not return_pymupdf_moduleSpec:
        raise PrettyErrorDisplay("Unable to proceed. PyMuPDF is not found on your machine.")

    validated_dict = validate_pdf_dict(items, source, exclude, excludeSource)

    # If user passes a sort order, update the previous list. Will happen after list validation
    if sort:
        log.debug("Sorting files...")
        validated_dict = sort_dict(sort, validated_dict)
    
    merge_runtime(validated_dict, output, preserve, sort)