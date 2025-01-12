import typer
from click.exceptions import ClickException
import fitz  # fitz is actually PyMuPDF
import magic
import os

from typing import List  # Needed for getting more than 1 argument in command-line
from typing_extensions import Annotated
from enum import Enum

from rich.panel import Panel
from rich.table import Table
from rich import print

app = typer.Typer()
workingDir = os.getcwd() # use this var on functions that calls os.getcwd() more than once


class PrettyErrorDisplay(ClickException):
    """
    Raised when the program does something it wasn't supposed to. Imports from Click.exceptions.ClickException
    """


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
    

def sortList(sort_type, items):
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


def hasPdfExtension(item: str) -> bool:
    """
    Returns the filetype by checking if it endswith .pdf
    Doesn't use name.endswith("pdf") because files like file/pdf returns True if used.
    Will return false if the item is just "pdf" and nothing else

    Args:
        item (str): filePath

    Returns:
        bool: Are you a PDF format? 
    """
    return item.lower().split(".")[-1] == "pdf" and item != "pdf"


def getFileBaseName(item: str) -> str:
    """
    Returns the basename of a filepath

    Args:
        item (str): filepath 

    Returns:
        str: basename of the filepath
    """
    return os.path.basename(item)


def getFileDirName(item:str) -> str:
    """
    Returns the directory folder path of the file

    Args:
        item (str): filepath

    Returns:
        str: folder of the filepath
    """
    return os.path.dirname(item)


def getFileFullPath(folderpath:str, filename:str) -> str:
    """
    Returns absolute path of a file by combining folderpath and filename

    Args:
        folderpath (str): folder name
        filename (str): file Name

    Returns:
        str: Full path of a file
    """
    return os.path.join(folderpath, filename)


def getPDFfromDirectory(directory: str) -> list:
    """
    Gets PDFs from a directory. 
    Only used in the validateListForPDF when the user passes a directory address instead of the filename

    Args:
        directory (str): Directory path

    Returns:
        list: Pdf files from the list
    """

    directory = workingDir if "." in directory else directory
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = getFileFullPath(directory, folder_item)
        if hasPdfExtension(folder_path): pdf_files.append(folder_path)

    return pdf_files


def validateListForPDF(items, exclude, mimeCheck):
    """
    List Validation of eligible PDF files.
    Takes a list and removes incompatible item from the lists

    Args:
        items (list): Unchecked list of str as file path
        exclude (list) : List of excluded files that will remove from items
        mimeCheck (bool): Mimecheck of files using bool

    Raises:
        PrettyErrorDisplay: Typer Exception if list has less than 2 PDF files

    Returns:
        list: Validated list of PDF files
    """
    validFileItems = []
    for item in items:
        if item not in validFileItems and hasPdfExtension(item): validFileItems.append(os.path.abspath(item))
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else item} [/yellow]")
            # Note: "." is actually an address to the current directory
            # TODO: check if the program can run if there is a fake pdf in the current directory
            validFileItems.extend(getPDFfromDirectory(item))
        else: print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] {item} [/i]")

    # Sorts the list previously from set to remove duplicates and checks for exclude to remove. 
    # [] is for NoneType to allow iteration of list
    validFileItems = sorted(list(set([i for i in validFileItems or [] if i not in (exclude or [])])))

    # Performs mimechecking of the file. Changes the list
    if mimeCheck:
        print("\n[green]File mimechecking enabled.[/green]")
        for item in validFileItems:
            if magic.Magic(mime=True).from_file(item) != "application/pdf":
                print(f"[yellow]CAUTION! Automatic Merge Target Ignore. [bold red]{item}[/bold red] is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'[/yellow]")
                validFileItems.remove(item)
    else:
        print("\n[orange]Fake PDF files cannot be detected. Use '-m' to enable file mime checking \n[/orange]")

    # List needs to be more than 1 validated pdf to work with merge
    if len(validFileItems) <= 1:
        raise PrettyErrorDisplay(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return validFileItems


def validateWorkingDirectory(filePath):
    """
    Validation of the folder path
    Checks if a folder path exists.
    If it doesn't, then create a folder for that path. Otherwise, the working script directory will be the saving folder path.
    If the folder path exists then the target folder path will be the saving folder path.

    Args:
        filePath (str): Path of the file

    Returns:
        str: Validated File folder path
    """

    trueFolderPath = getFileDirName(filePath)  # in case someone throws a directory of a file
    doesPathExist = os.path.isdir(trueFolderPath)

    if not doesPathExist:
        folder_creation_choice = typer.confirm(f"\nCaution! Saving folder '{trueFolderPath}' doesn't exist\nDo you wish to create it?")
        if folder_creation_choice:
            os.makedirs(trueFolderPath, exist_ok=True)
        else:
            print("\n[yellow]Custom folder path creation aborted.[/yellow] Working directory will be the saving directory.")
            trueFolderPath = workingDir

    return trueFolderPath


def validateOverWrite(target_dir:str) -> bool:
    """
    Prompts y/n as bool to get permission either to overwrite existing file or not.
    Uses Typer.confirm

    Args:
        target_dir (str): filepath of the saving directory

    Returns:
        bool: Do you want to overwrite or not?
    """
    return typer.confirm(f"\n{getFileBaseName(target_dir)} already exists. Do you want to overwrite this file?")


def validateFileName(target_file_path):
    """
    Checks the filetype of the target directory filename.
    this will keep causing a prompt if the filetype doesn't match the correct type or the filename is SUS.
    Only runs if the user wants to add a custom filename instead of the default.

    Args:
        target_file_path (_type_): _description_

    Returns:
        _type_: _description_
    """
    filename = getFileBaseName(target_file_path)
    folderpath = getFileDirName(target_file_path)
    print(filename, folderpath)
    while True:
        if not hasPdfExtension(filename):
            print(f"\nInvalid FileType name. Expected 'pdf'. Got {filename.lower().split(".")[-1]}")
            filename = typer.prompt("Enter saving filename: ")
            continue

        elif os.path.exists(getFileFullPath(folderpath, filename)):
            # if the output already leads to an existing file and then user doesn't want to overwrite so they add another file
            #  and AGAIN make the same mistake like before, prompt them again!
            print(f"\nChanged file name ({filename}) already exists")
            if not validateOverWrite(getFileFullPath(folderpath, filename)):
                print("Filename cannot be same if overwrite isn't allowed.")
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break
    return getFileBaseName(filename)  # This function will return basename only. Path dir is not accepted.


def validateOutputFileName(target_file_path):
    """
    Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        validated_target_file_path (str): validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    outputFileName = ""
    folder_path = (workingDir if getFileDirName(target_file_path) == "" else getFileDirName(target_file_path))
    while True:
        outputFileName = validateFileName(target_file_path)
        working_dir = validateWorkingDirectory(getFileFullPath(folder_path, outputFileName))
        break

    return getFileFullPath(working_dir, outputFileName)


def displaySuccessfulMerge(outputPath:str):
    """
    Display Successfull merge output. Shows output file location

    Args:
        outputPath (str) : saving directory of the file
    """

    print(Panel(f"""
File name: [i]{getFileBaseName(outputPath)}[/i]
Folder: [i]{workingDir if getFileDirName(outputPath) == "" else getFileDirName(outputPath)}[/i]
""", subtitle="MERGE COMPLETED", border_style="green", expand=False))


def deleteTemporaryCreatedFolder(outputPath: str):
    """
    Allow user to delete their newly-created saving directory
    Since we created this during process, we can delete it before the program ends
    The idea is that this directory if created is still empty. We have not transferrred anything here yet.

    Args:
        outputPath (str): Saving folder of the output file

    Raises:
        PrettyErrorDisplay: If the merge runtime comes to an error.
    """
    outputSavingFolder = getFileDirName(outputPath)
    if not (workingDir == outputSavingFolder) and len(os.listdir(outputSavingFolder)) == 0: 
        try:
            print(f"Deleting temporary directory ({outputSavingFolder})....")
            os.rmdir(outputSavingFolder)
        except Exception as e:
            print(f"[red]Error deleting temporary directory: {e} \nTarget path: {outputSavingFolder}[/red]")


def displayMergeOverview(itemsList:list, outputPath:str, sort:str):
    """
    Overview of the entire task before the start of the job.
    Uses Panel and Table from Rich.

    Args:
        itemsList (list): validated list of pdf filenames
        outputFile (str): output file str
        sort (str): sorting method of the list items
    """
    fileSize = 0
    table = Table(show_header=False, show_lines=True, highlight=True)
    ordered_file_list_view = f"{"\n".join(f"{index+1}. ITEM: [blue]{getFileBaseName(item)}[/blue] | DIRECTORY: [yellow]{getFileDirName(item)}[/yellow]" for index, item in enumerate(itemsList))}"

    # Calculate estimated size of the merge
    for i in itemsList: fileSize += os.path.getsize(i) / (1024 * 1024)
    table.add_row("[bold][u]Files to be merged[/u][/bold]:\n(as merge order)", ordered_file_list_view)
    table.add_row("[bold][u]Output file[/u][/bold]:" , f"[i]{getFileBaseName(outputPath)}[/i]")
    table.add_row("[bold][u]Saving directory[/u][/bold]:", f"[italic yellow]{getFileDirName(outputPath)}[italic yellow]")
    table.add_row("[bold][u]Sort Order Mode (Optional)", f"{sort} ([i]{"No active sorting" if sort == None else sort.description() }[/i]) ")
    table.add_row("[bold][u]Estimated Size[/u][/bold]:", f">{fileSize: .2f} MB")
    print(Panel(table, subtitle="[i]MERGING OVERVIEW[/i]", border_style="blue", expand=False))


def generateMergedPdfs(itemsList:list, outputFile:str, preserveFiles:bool):
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


def mergeRuntime(itemsList:list, output:str, preserveFiles:bool, sort:str):
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

    # TODO: You used syntax like workingDir if ... more than 3 times. Find a way to refactor this code.
    savingFileFolder = workingDir if getFileDirName(output) == "" else getFileDirName(output)
    outputFilePath = getFileFullPath(savingFileFolder, output)

    displayMergeOverview(itemsList, outputFilePath, sort)
    
    if typer.confirm("\nContinue with these settings?"):
        generateMergedPdfs(itemsList, outputFilePath, preserveFiles)
        displaySuccessfulMerge(outputFilePath) # Print success
    else:
        deleteTemporaryCreatedFolder(outputFilePath)


def merge(
    items: Annotated[List[str], typer.Argument(help="PDF files to merge.", rich_help_panel="Required")],
    sort: Annotated[SortOrder, typer.Option(case_sensitive=False, help="Sort files for order-specific merging", rich_help_panel="Additional Options")] = None,
    exclude: Annotated[List[str], typer.Option(help="Specify files to exclude from merging. You can specify exact file path depending on how you have added a folder directory", rich_help_panel="Additional Options")]=[None],
    mimecheck: Annotated[bool, typer.Option("--mimecheck/--no-mimecheck", "-m/-nm", help="Performs a PDF file mime check. Files that failed the check will be removed from selection.", rich_help_panel="Options")]=True,
    preserve: Annotated[bool, typer.Option("--preserve/--no-preserve", "-p/-np", help="Preserve the files after merging..", rich_help_panel="Options")] = True,
    validate: Annotated[bool, typer.Option("--validate/--no-validate", "-v/-nv", help="Enable/Disable validation of PDF files before execution", rich_help_panel="Feature Behavior")] = True,
    output: Annotated[str, typer.Option("--output", "-o", help="Save output file name. Can Accept a folder directory as well like folder/filename.pdf", rich_help_panel="Options")]="merged.pdf"):

    # in case someone is stupid to pass --mimencheck as --output
    if output == "--mimecheck" or output == "-m":
        raise PrettyErrorDisplay("--mimecheck mode can't be used with --output. Use --output to specify output file.")
    
    # conditional validation
    if validate:
        items = validateListForPDF(items, exclude, mimecheck)
        # if outputFileName or filepath is not default then it will trigger its validation process
        output = validateOutputFileName(output) if output != "merged.pdf" else "merged.pdf"


    # If user passes a sort order, update the previous list
    # Needs to happen after validated list
    if sort: items = sortList(sort, items)
    mergeRuntime(items, output, preserve, sort)