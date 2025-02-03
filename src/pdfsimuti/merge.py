import typer
import fitz
import os
import re

from typing import List  # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated
from enum import Enum

from rich.panel import Panel
from rich.table import Table
from rich import print

from pdfsimuti.setting import get_full_path, has_pdf_extension, validate_pdf_list  # Get common Function
from pdfsimuti.setting import workingDir           # Get common Variable
from pdfsimuti.setting import PrettyErrorDisplay   # Get common Class
app = typer.Typer()

create_directory = False

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


def confirm_file_overwrite(target_dir:str) -> bool:
    """
    Prompts y/n as bool to get permission either to overwrite existing file or not.
    Uses Typer.confirm

    Args:
        target_dir (str): filepath of the saving directory

    Returns:
        bool: Do you want to overwrite or not?
    """
    return typer.confirm(f"\n{return_filepath_basename(target_dir)} already exists. Do you want to overwrite this file?")


def designate_saving_dirpath(filePath:str) -> str:
    """
    Designation of the folder path
    Checks if a folder path exists.
    If it doesn't, then create a folder for that path. Otherwise, the working script directory will be the saving folder path.
    Otherwise, the target Path will be the saving dir.


    Args:
        filePath (str): Path of the file

    Returns:
        str: Validated File folder path
    """

    saving_dirname = return_filepath_dirname(filePath)  # in case someone throws a directory of a file
    global create_directory

    # Start custom saving directory if only the saving directory won't be the working directory.
    if not os.path.isdir(saving_dirname):

        folder_creation_choice = typer.confirm(f"\nCaution! Saving folder [blue]'{saving_dirname}'[/blue] doesn't exist\nDo you wish to create it?", prompt_suffix="\nDo not write reserved str or creation will be aborted!!")

        if folder_creation_choice:
            os.makedirs(saving_dirname, exist_ok=True)
            create_directory = True
        else:
            print("\n[yellow]Custom folder path creation aborted. [/yellow] Working directory will be the saving directory.")
            saving_dirname = workingDir

    return os.path.abspath(saving_dirname)


def designate_saving_filename(target_file_path:str) -> str:
    """
    Checks the filetype of the target directory filename.
    this will keep causing a prompt if the filetype doesn't match the correct type or the filename is SUS.
    Only runs if the user wants to add a custom filename instead of the default.

    Args:
        target_file_path (str): output file path

    Returns:
        str_type_: File name of the validated file.
    """
    filename = return_filepath_basename(target_file_path)
    folderpath = return_filepath_dirname(target_file_path)
    while True:
        if not has_pdf_extension(filename):
            print(f"\nInvalid FileType name. Expected 'pdf'. Got {filename.lower().split(".")[-1]}")
            filename = typer.prompt("Enter saving filename: ")
            continue

        elif os.path.exists(get_full_path(folderpath, filename)):
            # if the output already leads to an existing file and then user doesn't want to overwrite so they add another file
            #  and AGAIN make the same mistake like before, prompt them again!
            print(f"\nChanged file name ({filename}) already exists")
            if not confirm_file_overwrite(get_full_path(folderpath, filename)):
                print("Filename cannot be same if overwrite isn't allowed.")
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break
    return return_filepath_basename(filename)  # This function will return basename only. Path dir is not accepted.


def designate_saving_filePath(target_file_path:str) -> str:
    """
    Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        str: Abstract validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    outputFileName = ""
    folder_path = (workingDir if return_filepath_dirname(target_file_path) == "" else return_filepath_dirname(target_file_path))
    while True:
        outputFileName = designate_saving_filename(target_file_path)
        # TODO: designate_saving_dirpath only needs the dirpath. not the complete filepath.
        # TODO: Get the full path of working_dir
        working_dir = designate_saving_dirpath(get_full_path(folder_path, outputFileName))
        break
    
    return get_full_path(working_dir, outputFileName)


def show_successful_merge_outcome(outputPath:str):
    """
    Display Successfull merge output. Shows output file location

    Args:
        outputPath (str) : saving directory of the file
    """

    print(Panel(f"""
File name: [i]{return_filepath_basename(outputPath)}[/i]
Folder: [i]{workingDir if return_filepath_dirname(outputPath) == "" else return_filepath_dirname(outputPath)}[/i]
""", subtitle="MERGE COMPLETED", border_style="green", expand=False))


def delete_temp_dir(folderOutputPath: str):
    """
    Allow user to delete their newly-created saving directory.
    Takes a path and gets the dirname from it.
    
    If the dirname isn't the working dir or the dir isn't empty; delete the dir.

    Args:
        folderOutputPath (str): Saving folder of the output file

    Raises:
        PrettyErrorDisplay: If the merge runtime comes to an error.
    """
    if not (workingDir == folderOutputPath) and len(os.listdir(folderOutputPath)) == 0 and os.path.exists(folderOutputPath) and create_directory: 
        try:
            print(f"Deleting temporary directory [red]({folderOutputPath})[/red]")
            os.rmdir(folderOutputPath)
        except Exception as e:
            print(f"[red]Error deleting temporary directory: {e} \nTarget path: {folderOutputPath}[/red]")


def view_merge_overview(itemsList:list, outputPath:str, sort:str):
    """
    Overview of the entire task before the start of the job.
    Uses Panel and Table from Rich.

    Args:
        itemsList (list): validated list of pdf filenames
        outputPath (str): output file str
        sort (str): sorting method of the list items
    """
    fileSize = 0
    table = Table(show_header=False, show_lines=True, highlight=True)
    ordered_file_list_view = f"{"\n".join(f"{index+1}. ITEM: [blue]{return_filepath_basename(item)}[/blue]\n   DIRECTORY: [yellow]{return_filepath_dirname(item)}[/yellow]" for index, item in enumerate(itemsList))}"

    # Calculate estimated size of the merge
    for i in itemsList: fileSize += os.path.getsize(i) / (1024 * 1024)
    table.add_row("[bold][u]Files to be merged[/u][/bold]:\n(as merge order)", ordered_file_list_view)
    table.add_row("[bold][u]Output file[/u][/bold]:" , f"[i]{return_filepath_basename(outputPath)}[/i]")
    table.add_row("[bold][u]Saving directory[/u][/bold]:", f"[italic yellow]{return_filepath_dirname(outputPath)}[italic yellow]")
    table.add_row("[bold][u]Sort Order Mode (Optional)[/bold]", f"{sort} ([i]{"No active sorting" if sort == None else sort.description() }[/i]) ")
    table.add_row("[bold][u]Estimated Size[/u][/bold]:", f">{fileSize: .2f} MB")
    print(Panel(table, subtitle="[i]MERGING OVERVIEW[/i]", border_style="blue", expand=False))


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
    Handles the arrangement of functions to handle merge functionality

    Args:
        itemsList (list): validated List of PDFs to merge
        output (str): output name of the merged pdf
        preserveFiles (bool): preserving files after completion confirmation
        sort (str): sorting method of the list items

    Raises:
        PrettyErrorDisplay: Exit the runtime after played to confirm runtime
    """
        # Warn user of immediate deletion if preserve is off
    if not preserveFiles: 
        print("[underline bold red]ACTIONS CAUTION! Preserving of files is OFF. Original merging files will be deleted after merging![/underline bold red]")

    view_merge_overview(itemsList, output, sort)
    
    if typer.confirm("\nContinue with current settings"):
        generate_merged_pdf(itemsList, output, preserveFiles)
        show_successful_merge_outcome(output) # Print success
    else:
        delete_temp_dir(return_filepath_dirname(output))


def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge.", rich_help_panel="Required")],
    sort: Annotated[SortOrder, typer.Option(case_sensitive=False, help="Sort files for order-specific merging", rich_help_panel="Additional Options")] = None,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF file mime check. Files that failed the check will be removed from selection.", rich_help_panel="Options")]=True,
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    output: Annotated[str, typer.Option("--output", "-o", help="Save output file name. Can Accept a folder directory as well like folder/filename.pdf", rich_help_panel="Options")]="merged.pdf"):

    # in case someone is stupid to pass --mimencheck as --output
    if output == "--mimecheck" or output == "-m":
        raise PrettyErrorDisplay("--mimecheck mode can't be used with --output. Use --output to specify output file.")
    
    items = validate_pdf_list(items, exclude, mimecheck)
    output = designate_saving_filePath(output)

    # If user passes a sort order, update the previous list
    # Needs to happen after validated list
    if sort: items = sort_list(sort, items)
    merge_runtime(items, output, preserve, sort)