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

from pdfsimuti.utils import get_full_path, has_pdf_extension, validate_pdf_list, display_rejected_files  
from pdfsimuti.utils import workingDir, DEFAULT_SAVE_PDF_FILENAME         
from pdfsimuti.utils import PrettyErrorDisplay     

                    
app = typer.Typer()

# TODO: Optimize the code between output designation + merge_runtime and try to change all os.path with pathlib (check performance comparison first) 

class SortOrder(str, Enum):
    """
    Contains function that handles the sorting of 

    Args:
        str : sort type
        Enum (list): sort type options. Specific to Typer.

    Returns:
        str: sort type and its description
    """
    name = "name"
    name_reverse = "name_reverse"
    modified = "modified"

    def __str__(self):  
        return self.name.replace("_", " ").capitalize() # Get the name of the class value
    
    def description(self):
        description = {
            SortOrder.name : "Files are arranged alphabetically",
            SortOrder.name_reverse : "Files are arranged alphabetically reversed",
            SortOrder.modified : "Files are arranged based on their modified dates"
        }
        return description.get(self)
    

def sort_list(sort_type, items):
    """
    Sorts a list of items based on the specified sort type.

    Args:
        sort_type (str): The type of sort to perform.
        items (list): The list of items to sort.
    
    Returns:
        items (list): Sorted List
    """
    # Dictionary-Based Approach
    sort_methods = {
        "name": lambda: items.sort(),
        "name_reverse": lambda: items.sort(reverse=True),
        "modified": lambda: sorted(items, key= lambda x: os.path.getmtime(x))
    }
    sort_methods.get(sort_type)()
    return items


def return_filepath_basename(item: str) -> str:
    """
    Returns the basename of a filepath.
    Created if the user sends a path outside of the active directory

    Args:
        item (str): filepath 

    Returns:
        str: basename of the filepath
    """
    return os.path.basename(item)


def return_filepath_dirname(item:str) -> str:
    """
    Returns the directory folder path of the file

    Args:
        item (str): filepath

    Returns:
        str: folder of the filepath
    """
    return os.path.dirname(item)


def designate_saving_dirname(filePath) -> str:
    """
    Designation of the folder path
    Checks if a folder path exists.
    If it doesn't, then confirm the user of new folder creation.
    
    If the user denies that, folder will be the same as given before and be created later on in `merge_runtime()`

    Args:
        filePath (str): Path of the file

    Returns:
        str: Validated File folder path. Path is absolute path.
    """
    if not os.path.isdir(filePath):
        print(f"[yellow]\nCAUTION![/yellow] Saving folder '{filePath}' doesn't exist")
        folder_creation_choice = typer.confirm(f"Do you wish to create it?")
        if not folder_creation_choice:
            print("\n[yellow]Custom folder path creation aborted.[/yellow] Working directory will be the saving directory.")
            filePath = workingDir
            
        # if you are wondering where the os.makedirs is happening, its not here but rather on the merge_runtime()
        # if you are to create it here, either overview had to be scrapped or you cannot notify the user of new folder creation 
        # or you have to use a global variable

    return os.path.abspath(filePath)


def designate_saving_filename(target_file_path:str) -> str:
    """
    Checks the filetype of the target directory filename.
    this will keep causing a prompt if the filetype doesn't match the correct type or the filename is SUS.
    Only runs if the user wants to add a custom filename instead of the default.

    Args:
        target_file_path (str): output file path

    Returns:
        str: File name of the validated file.
    """
    # if user gives something like folder/ then the filename will be default or otherwise it will be '' which is bad.
    filename = DEFAULT_SAVE_PDF_FILENAME if return_filepath_basename(target_file_path) == "" else return_filepath_basename(target_file_path) 
    folderpath = return_filepath_dirname(target_file_path)
    
    while True:
        if not has_pdf_extension(filename):
            print(f"\nInvalid FileType name. Expected 'pdf'. Got {filename.lower().split(".")[-1]}")
            filename = typer.prompt(f"Enter saving filename (such as {DEFAULT_SAVE_PDF_FILENAME}): ")
            continue

        elif os.path.exists(get_full_path(folderpath, filename)): # Takes the updated filename only. Check above

            # if the output already leads to an existing file and then user doesn't want to overwrite so if they add another file
            #  and AGAIN make the same mistake like before then prompt them again!
            print(f"\n[yellow]CAUTION![/yellow] Output PDF filename '[i]{filename}[/i]' already exists.")
            
            if not typer.confirm("Do you wish to overwrite this file?"):    
                print("Filename cannot be same if overwrite isn't allowed")
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break
    
    return return_filepath_basename(filename)  # This function will return basename only. Path dir is not accepted.


def designate_saving_filePath(target_file_path):
    """
    Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        str: Abstract validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path for scanning
    target_file_basename = return_filepath_basename(target_file_path)
    target_file_dirname = return_filepath_dirname(target_file_path)
    folder_path = workingDir if target_file_dirname == "" else target_file_dirname
    
    working_dir = designate_saving_dirname(folder_path)
    outputFileName = designate_saving_filename(get_full_path(working_dir, target_file_basename))

    return get_full_path(working_dir, outputFileName)


def show_successful_merge_outcome(outputPath:str):
    """
    Display Successfull merge output. Shows output file location

    Args:
        outputPath (str) : saving directory of the file
    """

    print(Panel(f"""
Filename: [i]{return_filepath_basename(outputPath)}[/i]
Folder: [i]{workingDir if return_filepath_dirname(outputPath) == "" else return_filepath_dirname(outputPath)}[/i]
Fullpath: [i]{outputPath}[/i]
""", subtitle="MERGE COMPLETED", border_style="green", expand=False))


def view_merge_overview(itemsList:list, outputPath:str, preserve_Files: bool, sort:str):
    """
    Overview of the entire task before the start of the job.
    Uses Panel and Table from Rich.

    Args:
        itemsList (list): validated list of pdf filenames
        outputFile (str): output file str
        sort (str): sorting method of the list items
    """
    fileSize = 0
    table = Table(show_header=False, show_lines=True, highlight=True, expand=True)
    ordered_file_list_view = f"{"\n".join(f"{index+1}. ITEM: [blue]{return_filepath_basename(item)}[/blue]\n   DIRECTORY: [yellow]{return_filepath_dirname(item)}[/yellow]" for index, item in enumerate(itemsList))}"

    # Calculate estimated size of the merge
    for i in itemsList: fileSize += os.path.getsize(i) / (1024 * 1024)
    table.add_row("[underline bold]Files to be merged[/underline bold]:\n(as merge order)", ordered_file_list_view)
    table.add_row("[underline bold]Output file[/underline bold]:" , f"[i]{return_filepath_basename(outputPath)}[/i]")
    table.add_row("[underline bold]Saving directory[/underline bold]:", f"[italic yellow]{return_filepath_dirname(outputPath)}[italic yellow]")
    table.add_row("[underline bold]Sort Order Mode (Optional):", f"{sort} [i]({"Sorting based on arragement" if sort == None else sort.description() })[/i] ")
    table.add_row("[underline bold]Preserve Mode:[/underline bold]", f"[italic bold]{"[green]Preserve ON![/green]" if preserve_Files else "[red]Preserve OFF![/red] PDF files will be deleted after merging."}[italic bold]")
    table.add_row("[underline bold]Estimated Size[/underline bold]:", f">{fileSize: .2f} MB")
    
    print("\nPlease confirm the job.")
    print(Panel(table, subtitle="[i]MERGING OVERVIEW[/i]", border_style="blue", expand=True))


def generate_merged_pdf(itemsList:list, outputFile:str, preserveFiles:bool):
    """
    Main engine of the pdf. Uses PyMuPDF to merge files

    Args:
        itemsList (list): validated list of pdf filenames
        outputFile (str): output file str
        preserveFiles (bool): preserving files after completion confirmation

    Raises:
        PrettyErrorDisplay: Display error if failed to merge
    """
    try:
        doc = fitz.open()
        for file in itemsList:
            doc.insert_file(file)
            # Remove files if preserve is removed
            if not preserveFiles:
                os.remove(file)
        doc.save(outputFile)
        
    # If output directory specified doesn't exist
    except Exception as e:  raise PrettyErrorDisplay(f"Error. \n{e}")


def merge_runtime(itemsList:list, output:str, preserveFiles:bool, sort:str):
    """
    Runtime of the merge feature
    Handles the arrangement of functions for merging

    Args:
        itemsList (list): validated List of PDFs to merge
        output (str): output name of the merged pdf
        preserveFiles (bool): preserving files after completion confirmation
        sort (str): sorting method of the list items

    """
    output = designate_saving_filePath(output)
    view_merge_overview(itemsList, output, preserveFiles, sort)
    
    if typer.confirm("\nContinue with current settings"):
        if not os.path.isdir(Path(output).parent): os.makedirs(Path(output).parent)
        generate_merged_pdf(itemsList, output, preserveFiles)
        show_successful_merge_outcome(output) # Print success


def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge.", rich_help_panel="Required")],
    sort: Annotated[SortOrder, typer.Option(case_sensitive=False, help="Sort files for order-specific merging", rich_help_panel="Additional Options")] = None,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF file mime check. Files that failed the check will be removed from selection.", rich_help_panel="Options")]=True,
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    validate: Annotated[bool, typer.Option("--validate/--no-validate", "-v/-nv", help="Enable/Disable validation of PDF files before execution", rich_help_panel="Feature Behavior")] = True,
    output: Annotated[str, typer.Option("--output", "-o", help="Save output file name. Accepted formats like folder/file.pdf, file.pdf, folder/", rich_help_panel="Options")]=DEFAULT_SAVE_PDF_FILENAME):

    # in case someone is stupid to pass --mimencheck as --output
    if output == "--mimecheck" or output == "-m":
        raise PrettyErrorDisplay("--mimecheck mode can't be used with --output. Use --output to specify output file.")
    
    # conditional validation
    if validate:
        items = validate_pdf_list(items, exclude, mimecheck)
        display_rejected_files()

    
    # If user passes a sort order, update the previous list. Will happen after list validation
    if sort: items = sort_list(sort, items)
    merge_runtime(items, output, preserve, sort)