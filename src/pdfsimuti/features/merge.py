import typer
import fitz
import os
import re

from typing import List  # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated, Optional
from enum import Enum
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from rich import print

from pdfsimuti.utils import return_basename, return_dirname, return_abspath, return_confirm
from pdfsimuti.utils import validate_pdf_dict, exit_program
from pdfsimuti.utils import PrettyErrorDisplay, CURRENT_DIR, DEFAULT_OUTPUT

app = typer.Typer()

class SortOrder(str, Enum):
    """
    Contains function that handles the ordering for the merge by sorting them.

    Args:
        str : sort type
        Enum (list): sort type options. Specific to Typer.

    Returns:
        str: sort type and its description
    """
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


def sort_natural(files_dict, reverse=False):

    def nat(item):
        return [
            int(item) if item.isdigit() else item.lower() for item in re.split(r'(\d+)', item) # turns a string into letters and digits
        ]
    
    nonwhitespace = [(position, item.replace(" ", "")) for position, item in enumerate(files_dict, start=0)]
    val_sort = sorted(nonwhitespace, key=lambda item: nat(item[1]), reverse=reverse)
    result =  {
        key: files_dict[key]
        for _, key in val_sort
    }
    return result


def sort_dict(sort_type, files_dict):
    """
    Sort a dictionary of file paths based on the specified criteria.

    Args: 
        sort_type (str): The sorting criterion ('name', 'reverse', 'modified' or 'creation).
        files_dict (dict): The dictionary of files to be sorted (keys are file paths).

    Returns:
        list: A sorted list of (key, value) tuples from the dictionary.
    """
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


def reserved_filenaming_charCheck(filename:str) -> bool:
    if re.search(r'[\"#$|<>:?*/(\)\\\"]', filename):
        return True
    return False


def designate_saving_filePath(target: str) -> str:
    import sys 

    savePath = Path(DEFAULT_OUTPUT) if target == "" else Path(target)
    folder_creation = False
    warned = False

    while Path(savePath):
        match Path(savePath):

            # if the user gives a filename like filename<>.pdf then it is an automatic False according to return_confirm()
            case subject if (not subject.resolve().is_relative_to("/home")) and sys.platform == "linux" and not warned:
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

            case subject if subject.exists():
                print("\n[yellow]CAUTION![/yellow] Specified output filepath already exists.")
                if not return_confirm("Do you wish to overwrite this file? (Default: Y)"):    
                    print("\nFilename cannot be same if overwrite isn't allowed")
                    savePath = Path(typer.prompt("Enter new output path or filename again: "))

            case subject if not (parent := subject.parent).exists() and not folder_creation:
                print(f"\n[yellow]CAUTION[/yellow] File directory [purple]{parent}[/purple] doesn't exist.")
                folder_creation = return_confirm("Create new directory?")
                if not folder_creation:
                    savePath = Path(typer.prompt("Enter new output path or filename again: "))
            case _:
                break

    return str(savePath)


def display_successful_merge_outcome(outputPath:str):
    """
    Display an outcome panel showing the successful merge operation and the final output file details.

    Args:
        outputPath (str): The absolute file path where the merged PDF was saved.
    """
    outcome_table = Table(show_header=False, expand=False, show_lines=True)
    outcome_table.add_row("[u][b]Filename[/b][/u]", return_basename(outputPath))
    outcome_table.add_row("[u][b]Folder[/b][/u]", CURRENT_DIR if return_dirname(outputPath) == "" else return_dirname(outputPath))
    outcome_table.add_row("[u][b]Absolute Path[/b][/u]", outputPath)

    print(Panel(outcome_table, subtitle="MERGE COMPLETED", border_style="green", expand=False))


def display_merge_overview(filesDict:dict, outputPath:str, preserveFiles: bool, sort:str):
    """
    Display a comprehensive panel showing all details of the upcoming PDF merge job for user confirmation.
    This includes the merge order, output path, estimated size, sorting method, and file preservation status.

    Args:
        filesDict (dict): A validated list of file entries (e.g., tuples or list items containing the file path at index 0).
        outputPath (str): The final, validated absolute path for the merged output file.
        preserveFiles (bool): Boolean flag indicating whether original files should be preserved or deleted after merging.
        sort (str): The sorting method applied to the file list (or 'None' if sorting based on initial arrangement).
    """
    from rich.console import Group
    from rich.console import Console
    from rich.rule import Rule
    from pdfsimuti.utils import return_validated_display # display file status despite the result

    fileSize = 0
    merge_table_details = Table(show_header=False, show_lines=True, highlight=True, expand=True)

    # Calculate estimated size of the merge
    for item in filesDict: fileSize += os.path.getsize(item) / (1024 * 1024)
    merge_table_details.add_row("[underline bold]Output file[/underline bold]:" , f'{"[yellow italic](Overwriting)[/yellow italic] " if os.path.exists(outputPath) else ""}' + f"{return_basename(outputPath)}")
    merge_table_details.add_row("[underline bold]Saving directory[/underline bold]:", f'{"[yellow italic](Overwriting)[/yellow italic] " if os.path.exists(outputPath) else ""}' + f"{CURRENT_DIR if return_dirname(outputPath) == "" else return_abspath(return_dirname(outputPath))}")
    merge_table_details.add_row("[underline bold]Sort Order[/underline bold]:", f"[i]({str(sort)})[/i] {SortOrder(sort).description()}")
    merge_table_details.add_row("[underline bold]Preserve Mode[/underline bold]:", f"{"[italic green bold]Preserve ON![/italic green bold] Files will not be deleted after merging." if preserveFiles else "[italic red bold]Preserve OFF! [/italic red bold]PDF files will be deleted after merging."}")
    merge_table_details.add_row("[underline bold]Estimated Size[/underline bold]:", f">{fileSize: .2f} MB")
    
    panel_group = Group(
        Rule("Merge Order Overview"),
        return_validated_display(filesDict),
        Rule("Merge Settings"),
        merge_table_details
    )
    Console().print(Panel(panel_group, border_style="blue", expand=False))
    if fileSize > 100: print(f"\nEstimated file size is big. Merge operations will take a while.")


def generate_merged_pdf(itemsDict:dict, outputFile:str, preserveFiles=True):
    """
    Execute the PDF merging operation using the PyMuPDF (fitz) library.

    It iterates through the dict of files and appends them sequentially into a single output document.

    Args:
        itemsDict (dict): A validated dict of file entries (e.g., tuples where index 0 is the file path) to be merged.
        outputFile (str): The final, absolute file path for the merged PDF output.

    Raises:
        PrettyErrorDisplay: If the merging process fails for any reason other than a KeyboardInterrupt.
    """ 
    import logging
    from rich.logging import RichHandler
    logging.basicConfig(
        level="NOTSET", format="%(message)s", datefmt="[%X]", handlers=[RichHandler()]
    )   
    log = logging.getLogger("rich")

    try:
        log.info("Started merge operations.")
        # in case the user approves overwrite.
        # if not done, this will remove the merged file if --no-preserve is active
        with fitz.open() as doc:
            for item_entry in itemsDict.keys():
                doc.insert_file(item_entry)
                log.info(f'Inserted file: {item_entry}')
            log.info("Finalizing saving.")
            doc.save(outputFile)
        
        if outputFile in itemsDict:
            itemsDict.pop(outputFile)

        # only delete after merging
        if not preserveFiles:
            for item_entry in itemsDict: 
                os.remove(item_entry)

        log.info("Merge operations completed.")
        
    except KeyboardInterrupt:
        exit_program()
    except ValueError:
        raise PrettyErrorDisplay(f"Fatal. PyMuPDF unable to read data. Run with mimechecking.")
    except Exception as e:  
        raise PrettyErrorDisplay(f"Program failed to run. \n{e}")


def merge_runtime(filesDict, output:str, preserveFiles:bool, sort:str):
    """
    Control the entire PDF merging process, orchestrating path validation, user overview confirmation, execution, and cleanup.

    It handles saving directory creation, calls the main merging engine, manages file deletion, and displays the final outcome.

    Args:
        filesDict (dict): A validated dict of PDF file entries to be merged.
        output (str): The user-defined output file path for the merged PDF.
        preserveFiles (bool): Boolean flag indicating whether original files should be preserved or deleted after a successful merge.
        sort (str): The sorting method applied to the dict of items before merging.
    """

    output = designate_saving_filePath(output)
    output_dir = Path(output).parent
    display_merge_overview(filesDict, output, preserveFiles, sort) # display overview to the user
    
    if return_confirm("\nMerge with current settings? (Default: N)", default=False):
        
        if not preserveFiles:
            print("[yellow]CAUTION![/yellow] [code]--no-preserve[/code] flag present! Files will be deleted after successful merge!")
            if not return_confirm("Proceed?"):
                exit_program()        
        if not os.path.isdir(output_dir): 
            try: os.makedirs(output_dir)
            except PermissionError:
                raise PrettyErrorDisplay(f"Program failed. Unable to create directory: {output_dir}")
        
        # purify dict of rejected items
        validated_dict = {key:value for key, value in filesDict.items() if value['valid'] == True}

        generate_merged_pdf(validated_dict, output, preserveFiles)
        # at this point, merge is sucessful
        display_successful_merge_outcome(output)
    else:
        exit_program()


def merge(
    items: Annotated[Optional[List[str]], typer.Argument(help="PDF files to merge. You can also use --source instead.")]=None,
    sort: Annotated[SortOrder, typer.Option(case_sensitive=False, help="Sort files for order-specific merging", rich_help_panel="Additional Options")] = SortOrder.none,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging.", rich_help_panel="Additional Options", metavar="FILEPATH")]=[],
    source: Annotated[Optional[str], typer.Option(help="Add files as filepaths from external files (.txt)", rich_help_panel="Additional options", metavar=".txt FILE")] = None,
    exclude_source: Annotated[Optional[str], typer.Option(help="Specify external file as exclude filepath source", rich_help_panel="Additional options", metavar=".txt FILE")] = None,
    
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF file mime check. Files that failed the check will be removed from selection.", rich_help_panel="Options")]=True,
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    output: Annotated[str, typer.Option("--output", "-o", help="Save output file name. Accepted formats like folder/file.pdf or file.pdf", rich_help_panel="Options")]=DEFAULT_OUTPUT):

    # in case someone pass --mimecheck as --output
    if output == "--mimecheck" or output == "-m" or output == "-nm" or output =="-no-mimecheck":
        raise PrettyErrorDisplay("--mimecheck flag can't be used after --output.")

    validated_dict = validate_pdf_dict(items, source, exclude, exclude_source ,mimecheck)

    # If user passes a sort order, update the previous list. Will happen after list validation
    if sort:
        validated_dict = sort_dict(sort, validated_dict)
    
    if items == None and not source:
        raise PrettyErrorDisplay("No filepaths were added to merge.py or with --source")

        
    merge_runtime(validated_dict, output, preserve, sort)
