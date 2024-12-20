import typer
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

def ifFilePDF(filename):
    """
    Returns the filetype by checking if it endswith .pdf
    """
    return filename.lower().split(".")[-1] == "pdf"


def getFileBaseName(fileStr):
    """
    Returns the directory basename of the file
    """
    return os.path.basename(fileStr)


def getFileDirName(fileStr):
    """
    Returns the directory folder path of the file
    """
    return os.path.dirname(fileStr)


def returnStrPath(folderpath, filename):
    """
    Returns absolute path of a file using os.path.join
    """
    return os.path.join(folderpath, filename)


def confirmTaskJob(itemsList, outputFileName, preserve_files, sort):
    """
    Overview of the entire task before the start of the job
    """
    savingFileFolder = workingDir if getFileDirName(outputFileName) == "" else getFileDirName(outputFileName)
    table = Table(show_header=False, show_lines=True, highlight=True)
    # Nothing special here
    ordered_file_list_view = f"{"\n".join(f"{index+1}. ITEM: [blue]{getFileBaseName(item)}[/blue] | DIRECTORY: [yellow]{getFileDirName(item)}[/yellow]" for index, item in enumerate(itemsList))}"

    # Calculate estimated size of the merge
    fileSize = 0
    for i in itemsList: fileSize += os.path.getsize(i) / (1024 * 1024)
    table.add_row("[bold][u]Files to be merged[/u][/bold]:\n(as merge order)", ordered_file_list_view)
    table.add_row("[bold][u]Output file[/u][/bold]:" , f"[i]{getFileBaseName(outputFileName)}[/i]")
    table.add_row("[bold][u]Saving directory[/u][/bold]:", f"[italic yellow]{savingFileFolder}[italic yellow]")
    table.add_row("[bold][u]Sort Order Mode (Optional)", f"{sort} ([i]{"No active sorting" if sort == None else sort.description() }[/i]) ")
    table.add_row("[bold][u]Estimated Size[/u][/bold]:", f">{fileSize: .2f} MB")
    print(Panel(table, subtitle="[i]MERGING OVERVIEW[/i]", border_style="blue", expand=False))

    # Warn user of immediate deletion if preserve is off
    if not preserve_files: print("[underline bold red]ACTIONS CAUTION! Preserving of files is OFF. Original merging files will be deleted after merging![/underline bold red]")

    if not typer.confirm("\nContinue with these settings?"):
        #BUG: Please taste the below line and modify the behavior if needed
        print(workingDir)
        print(savingFileFolder)

        # If the user crea
        if not (workingDir == savingFileFolder and os.path.isdir(savingFileFolder)): 
            try:
                print(f"Deleted temporary directory ({savingFileFolder})....")
                os.rmdir(savingFileFolder)
            except Exception as e:
                print(f"[red]Error deleting temporary directory: {e} \nTarget path:{savingFileFolder}[/red]")
        raise typer.Abort()

    return True

def removeDuplicates(listItems):
    filteredList = []
    for item in listItems:
        if item not in filteredList: filteredList.append(item)
    return filteredList

def getPDFfromDirectory(directory):
    """
    Gets PDFs from a directory. Only used in the validateListForPDF when the user passes a directory address instead of the filename
    """
    directory = os.getcwd() if "." in directory else directory
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = returnStrPath(directory, folder_item)
        if ifFilePDF(folder_path): pdf_files.append(folder_path)

    pdf_files.sort()
    return pdf_files


def validateListForPDF(items, exclude, mimeCheck):
    """List Validation of eligible PDF files

    Args:
        items (list): Unchecked list of str as file path
        exclude (list) : List of excluded files that will remove from items
        mimeCheck (bool): Mimecheck of files using bool

    Raises:
        typer.BadParameter: Typer Exception if list has less than 2 PDF files

    Returns:
        list: Validated list of PDF files
    """
    valid_items = []
    for item in items:
        if item not in valid_items and ifFilePDF(item): valid_items.append(os.path.abspath(item))
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else item}[/yellow]")
            # Note: "." is actually an address to the current directory
            valid_items.extend(getPDFfromDirectory(item))
        else: print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] {item} [/i]")

    # Remove duplicates if the user passes the same value more than once
    # Also remove excluded items if included in the exclude
    valid_items = [i for i in removeDuplicates(valid_items) if i not in exclude]

    if mimeCheck:
        print("\n[green]File mimechecking enabled.[/green]")
        for item in valid_items:
            if magic.Magic(mime=True).from_file(item) != "application/pdf":
                print(f"[yellow]CAUTION! Automatic Merge Target Ignore. [bold red]{item}[/bold red] is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'[/yellow]")
                valid_items.remove(item)
    else:
        print("\n[orange]mimecheck not enabled. Fake PDF files cannot be detected. Use '-m' to enable. \n[/orange]")

    # List needs to be more than 1 validated pdf to work with merge
    if len(valid_items) <= 1:
        raise typer.BadParameter(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return valid_items


def validateWorkingDirectory(target_file_path):
    """
    Validation of the folder path
    Checks if a folder path exists.
    If it doesn't, then create a folder for that path. Otherwise, the working script directory will be the saving folder path.
    If the folder path exists then the target folder path will be the saving folder path.

    Returns a validated folder path as str
    """
    trueFolderPath = getFileDirName(target_file_path)  # in case someone throws a directory of a file
    doesPathExist = os.path.isdir(trueFolderPath)

    if not doesPathExist:
        folder_creation_choice = typer.confirm(f"\nCaution! Saving folder '{trueFolderPath}' doesn't exist\nDo you wish to create it?")
        if folder_creation_choice:
            os.makedirs(trueFolderPath, exist_ok=True)
        else:
            print("\n[yellow]Custom folder path creation aborted.[/yellow] Working directory will be the saving directory.")
            trueFolderPath = workingDir

    return trueFolderPath


def validateOverWrite(target_dir):
    """
    Prompts y/n as bool to get permission either to overwrite existing file or not
    """
    return typer.confirm(f"\n{getFileBaseName(target_dir)} already exists. Do you want to overwrite this file?")


def validateFileName(target_file_path):
    """
    Checks the filetype of the target directory filename.
    this will keep causing a prompt if the filetype doesn't match the correct type or the filename is SUS.
    Only runs if the user wants to add a custom filename instead of the default.
    """
    filename = getFileBaseName(target_file_path)
    folderpath = getFileDirName(target_file_path)
    while True:
        # if file is not a pdf format
        if not ifFilePDF(filename) or filename == "pdf":
            print(f"\nInvalid FileType name. Expected 'pdf'. Got {filename.lower().split(".")[-1]}")
            filename = typer.prompt("Enter saving filename: ")
            continue

        elif os.path.exists(returnStrPath(folderpath, filename)):
            # if the output already leads to an existing file and then user doesn't want to overwrite so they add another file
            #  and AGAIN make the same mistake like before, prompt them again!
            print(f"\nChanged file name ({filename}) already exists")
            if not validateOverWrite(returnStrPath(folderpath, filename)):
                print("Filename cannot be same if overwrite isn't allowed.")
                filename = typer.prompt("Enter saving filename again: ")
                continue
        break

    return getFileBaseName(filename)  # This function will return basename only. Path dir is not accepted.


def validateOutputFileName(target_file_path):
    """Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        validated_target_file_path (str): validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    # Otherwise, saving directory will say "" in confirmTaskJob()
    final_filename = ""
    folder_path = (workingDir if getFileDirName(target_file_path) == "" else getFileDirName(target_file_path))
    while True:
        final_filename = validateFileName(target_file_path)
        working_dir = validateWorkingDirectory(returnStrPath(folder_path, final_filename))

        break
    return returnStrPath(working_dir, final_filename)


def printSuccessfulMerge(outputFileName):
    print(Panel(f"""
File name: [i]{getFileBaseName(outputFileName)}[/i]
Folder: [i]{workingDir if getFileDirName(outputFileName) == "" else getFileDirName(outputFileName)}[/i]
""", title="MERGE COMPLETED", border_style="green", expand=False))


def merge_runtime(input_file_list, outputFileName, preserve_files):
    """
    Takes 2 arguments, input_file_list and outputFileName
    This handles the main pdf merging.
    """
    try:
        doc = fitz.open()
        for file in input_file_list:
            doc.insert_file(file)
            # Remove files if preserve is removed
            if not preserve_files:
                os.remove(file)
        doc.save(outputFileName)
        printSuccessfulMerge(outputFileName) # Print success

    # If output directory specified doesn't exist
    except Exception as e:  raise typer.BadParameter(f"Error. \n{e}")
    except FileNotFoundError: raise typer.BadParameter(f"Error: File not found for merging!!")

class SortOrder(str, Enum):
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
    """
    # Dictionary-Based Approach
    sort_methods = {
        "name": lambda: items.sort(),
        "name_reverse": lambda: items.sort(reverse=True),
        "modified": lambda: sorted(items, key= lambda x: os.path.getmtime(x))
    }
    sort_methods.get(sort_type)()
    return items


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
        raise typer.BadParameter("--mimecheck mode can't be used with --output. Use --output to specify output file.")
    
    # conditional validation
    if validate:
        mergeFileList = validateListForPDF(items, exclude, mimecheck)
        # if outputFileName or filepath is not default then it will trigger its validation process
        outputFileName = validateOutputFileName(output) if (output != "merged.pdf" and not os.path.exists(output)) else "merged.pdf"
    else:
        mergeFileList, outputFileName = items, "merged.pdf"

    # If user passes a sort order, update the previous list
    # Needs to happen after validated list
    if sort: mergeFileList = sortList(sort, mergeFileList)

    # conditional confirmation
    if confirmTaskJob(mergeFileList, outputFileName, preserve, sort):
        merge_runtime(mergeFileList, outputFileName, preserve)

