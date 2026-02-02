import typer
import fitz
import os

from typing import List  # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated
from enum import Enum
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from rich import print

from pdfsimuti.utils import return_joined_filePath, return_basename, return_dirname, return_abspath, return_confirm
from pdfsimuti.utils import has_pdf_extension, validate_pdf_dict, exit_program
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
    normal = "normal"
    reverse = "reverse"
    modified = "modified"
    creation = "creation"

    def __str__(self):  
        return self.name.replace("_", " ").capitalize() # Get the name of the class value for overview
    

    def description(self):
        description = {
            SortOrder.normal : "Files are arranged alphabetically",
            SortOrder.reverse : "Files are arranged alphabetically reversed",
            SortOrder.modified : "Files are arranged based on their modified dates",
            SortOrder.creation : "Files are arranged based on their creation dates"
        }
        return description.get(self)
    

def sort_dict(sort_type: str, files_dict: dict):
    """
    Sort a dictionary of file paths based on the specified criteria.

    Args: 
        sort_type (str): The sorting criterion ('name', 'reverse', 'modified' or 'creation).
        files_dict (dict): The dictionary of files to be sorted (keys are file paths).

    Returns:
        list: A sorted list of (key, value) tuples from the dictionary.
    """
    match sort_type:
        case 'normal':
            return dict(sorted(files_dict.items()))
        case 'reverse':
            return dict(reversed(sorted(files_dict.items())))
        case 'modified':
            return dict(sorted(files_dict.items(), key=lambda item: os.path.getmtime(item[0])))
        case 'creation':
            return dict(sorted(files_dict.items(), key=lambda item: os.path.getctime(item[0])))
    

def advanced_filenaming(filename:str) -> str:
    """
    Handle risky or ambiguous filenames by presenting the user with interactive options to modify or replace the name.
    Options include ignoring, replacing characters, removing extensions, or manually inputting a new name.

    Args:
        filename (str): The original filename that was flagged as risky.
    
    Returns:
        str: The newly edited or user-provided filename.
    """
    from pdfsimuti.utils import text_dedent
    print(text_dedent(f"""
    -----------------------------------------------
    Detected risky filename ({filename}). Select option.
    
    [1] : Ignore warning and add extension to the end. [i]{filename}.pdf[/i]
    [2] : Change all "." to "-" then add extension to the end. [i]{filename.replace(".", "-")}.pdf[/i]
    [3] : Remove all "." then add extension. [i]{filename.lower().split(".")[0]}.pdf[/i]
    [0] : Enter a new name
    -----------------------------------------------
    """))
    while True:
        respond = input("> ")
        match respond:
            case "0":
                return input("Enter filename: ")
            case "1":
                return f"{filename}.pdf"
            case "2":
                return f"{filename.replace(".", "-")}.pdf"
            case "3":
                return f"{filename.lower().split(".")[0]}.pdf"
            case _:
                print("[red]Invalid input[/red]. Choose either 0,1,2 or 3.")
                continue
        break


def designate_dirname(filePath) -> str:
    """
    Validate and confirm the designated saving directory, prompting the user for creation if it doesn't exist.
    If denied, the saving folder defaults to the working directory; actual folder creation is deferred to ``merge_runtime()``.

    Args:
        filePath: The desired path for the output folder.

    Returns:
        str: The absolute path of the validated or defaulted output folder.
    """    
    if not os.path.isdir(filePath): 
        print(f"[yellow]\nCAUTION![/yellow] Save path non-existant: {filePath}")
        # add flag for root-level directory on linux OS
        import sys
        if sys.platform == "linux" and filePath[0:5] != "/home":
            print("[red]WARNING[/red]. Selected output filepath starts from linux root FHS. \nAbort immediately if you don't know what you're doing.")
            folder_creation_choice = return_confirm(caution=True)
            if not folder_creation_choice:
                exit_program()
        else:
            print("You can create a new folder there or choose current working directory")
            folder_creation_choice = return_confirm(f"Create new folder?")
        
        if not folder_creation_choice:
            print("\n[yellow]Custom folder path creation aborted.[/yellow] Working directory will be the saving directory.")
            filePath = CURRENT_DIR
            
        # if you are wondering where the os.makedirs is happening, its not here but rather on the merge_runtime()
        # if you are to create it here, either overview had to be scrapped or you cannot notify the user of new folder creation 
        # or you have to use a global variable
        # don't try that. i did it already.

    return return_abspath(filePath)


def designate_filename(target:str) -> str:
    """
    Validate and manage the designated output filename, ensuring it has a '.pdf' extension and handling existing file conflicts.
    It prompts the user to resolve non-PDF extensions or choose to overwrite an existing file.

    Args:
        target (str): The full output path provided by the user, which may include the folder and a custom filename.

    Returns:
        str: The final, validated basename of the file.
    """
    # if user gives something like folder/ then the filename will be default or otherwise it will be '' which is an error.
    filename = DEFAULT_OUTPUT if return_basename(target) == "" else return_basename(target) 
    folderpath = return_dirname(target)
    
    while True:
        if not has_pdf_extension(filename):
            file_extension = filename.lower().split(".")

            if len(file_extension) > 1:
                filename = advanced_filenaming(filename)
            else:
                filename = filename + ".pdf"
            continue

        elif os.path.exists(return_joined_filePath(folderpath, filename)):
            print(f"\n[yellow]CAUTION![/yellow] Output PDF filename '[i]{filename}[/i]' already exists.")
            
            if not return_confirm("Do you wish to overwrite this file?"):    
                print("\nFilename cannot be same if overwrite isn't allowed")
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break
    
    return return_basename(filename)  # This function will return basename only. Path dir is not accepted.


def designate_saving_filePath(target: str) -> str:
    """
    Validate and normalize the final output file path by separately processing and correcting the filename and the folder path.
    The process ensures a valid filename and confirms the existence (or creation) of the destination directory.

    Args:
        target (str): The user-provided output file path or directory address.

    Returns:
        str: The absolute, fully validated, and corrected file path for saving the output. Note that this path isn't validated as `os.path.exists()`
    """    
    # if user passes . then the working directory will be folder path for scanning
    target_file_basename = return_basename(target)
    target_file_dirname = return_dirname(target)
    
    working_dir = designate_dirname(return_abspath(target_file_dirname))
    outputFileName = designate_filename(return_joined_filePath(working_dir, target_file_basename))

    return return_joined_filePath(working_dir, outputFileName)


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
    merge_table_details.add_row("[underline bold]Output file[/underline bold]:" , f"[i]{return_basename(outputPath)}[/i]")
    merge_table_details.add_row("[underline bold]Saving directory[/underline bold]:", f"[italic yellow]{return_dirname(outputPath)}[italic yellow]")
    merge_table_details.add_row("[underline bold]Sort Order[/underline bold]:", f"{sort}. [i]{SortOrder(sort).description()}[/i] ")
    merge_table_details.add_row("[underline bold]Preserve Mode[/underline bold]:", f"[italic bold]{"[green]Preserve ON![/green]" if preserveFiles else "[red]Preserve OFF![/red]\nPDF files will be deleted after merging."}[italic bold]")
    merge_table_details.add_row("[underline bold]Estimated Size[/underline bold]:", f">{fileSize: .2f} MB")
    
    panel_group = Group(
        Rule("Merge Order Overview"),
        return_validated_display(filesDict),
        Rule("Merge Settings"),
        merge_table_details
    )
    print("\nPlease confirm the job.")
    Console().print(Panel(panel_group, border_style="blue", expand=False))


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
    try:
        # in case the user approves overwrite.
        # if not done, this will remove the merged file if --no-preserve is active
        with fitz.open() as doc:
            for item_entry in itemsDict: doc.insert_file(item_entry)
            doc.save(outputFile)
        
        if outputFile in itemsDict:
            itemsDict.pop(outputFile)

        # only delete after merging
        if not preserveFiles:
            for item_entry in itemsDict: 
                os.remove(item_entry)

    except KeyboardInterrupt:
        exit_program()
    except Exception as e:  raise PrettyErrorDisplay(f"Program failed to run. \n{e}")


def merge_runtime(filesDict:dict, output:str, preserveFiles:bool, sort:str):
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
    
    if return_confirm("\nMerge with current settings?", default=False):
        
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
        
        display_successful_merge_outcome(output) # Print success
    else:
        exit_program()

def merge(
        
    items: Annotated[List[str], typer.Argument(help="PDF files to merge.", rich_help_panel="Required")],
    sort: Annotated[SortOrder, typer.Option(case_sensitive=False, help="Sort files for order-specific merging", rich_help_panel="Additional Options")] = SortOrder.normal,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=None,
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF file mime check. Files that failed the check will be removed from selection.", rich_help_panel="Options")]=True,
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    output: Annotated[str, typer.Option("--output", "-o", help="Save output file name. Accepted formats like folder/file.pdf, file.pdf, folder/", rich_help_panel="Options")]=DEFAULT_OUTPUT):

    # in case someone pass --mimecheck as --output
    if output == "--mimecheck" or output == "-m" or output == "-nm" or output =="-no-mimecheck":
        raise PrettyErrorDisplay("--mimecheck flag can't be used after --output.")
    
    validated_dict = validate_pdf_dict(items, exclude, mimecheck)

    # If user passes a sort order, update the previous list. Will happen after list validation
    if sort:
        validated_dict = sort_dict(sort, validated_dict)
        
    merge_runtime(validated_dict, output, preserve, sort)
