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


def hasPdfExtension(item):
    """
    Returns the filetype by checking if it endswith .pdf
    Doesn't use name.endswith("pdf") because files like file/pdf returns True if used.
    Will return false if the item is just "pdf" and nothing else
    """
    return item.lower().split(".")[-1] == "pdf" and item != "pdf"


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


def getFileFullPath(folderpath, filename):
    """
    Returns absolute path of a file using os.path.join
    """
    return os.path.join(folderpath, filename)


def removeDuplicates(listItems):
    """
    This function removes the duplicates from the list using list comprehension
    This doesn't use something like list(set()) because that will randomize the list arrangment
    """
    filteredList = []
    for item in listItems:
        if item not in filteredList: filteredList.append(item)
    return filteredList


def getPDFfromDirectory(directory):
    """
    Gets PDFs from a directory. Only used in the validateListForPDF when the user passes a directory address instead of the filename
    """
    directory = workingDir if "." in directory else directory
    pdf_files = []
    for folder_item in os.listdir(directory):
        folder_path = getFileFullPath(directory, folder_item)
        if hasPdfExtension(folder_path): pdf_files.append(folder_path)

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
    validFileItems = []
    for item in items:
        if item not in validFileItems and hasPdfExtension(item): validFileItems.append(os.path.abspath(item))
        elif os.path.isdir(item):
            print(f"ADDDING FOLDER: [yellow]{"<CURRENT DIRECTORY>" if item == "." else item}[/yellow]")
            # Note: "." is actually an address to the current directory
            validFileItems.extend(getPDFfromDirectory(item))
        else: print(f"[red]WARNING![/red] FOLDER/ITEM not found: [i] {item} [/i]")

    # Remove duplicates if the user passes the same value more than once
    # Also remove excluded items if included in the exclude
    validFileItems = [i for i in removeDuplicates(validFileItems) if i not in exclude]

    if mimeCheck:
        print("\n[green]File mimechecking enabled.[/green]")
        for item in validFileItems:
            if magic.Magic(mime=True).from_file(item) != "application/pdf":
                print(f"[yellow]CAUTION! Automatic Merge Target Ignore. [bold red]{item}[/bold red] is not an PDF. Expected: 'application/pdf'. Got: '{magic.from_file(item)}'[/yellow]")
                validFileItems.remove(item)
    else:
        print("\n[orange]mimecheck not enabled. Fake PDF files cannot be detected. Use '-m' to enable. \n[/orange]")

    # List needs to be more than 1 validated pdf to work with merge
    if len(validFileItems) <= 1:
        raise typer.BadParameter(f"Searched over {len(items)} items. Excepted more than 1 compatible PDF file for merging.")

    return validFileItems


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
        #TODO: Refactor this codeline below yourself. Reduce it.
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
    """Extensive output file validation checker. Checks for filename first, then folder.

    Args:
        target_file_path (str): Directory address of the saving file on system

    Returns:
        validated_target_file_path (str): validated/corrected directory str to save the file
    """
    # if user passes . then the working directory will be folder path
    # Otherwise, saving directory will say "" in confirmTaskJob()
    outputFileName = ""
    folder_path = (workingDir if getFileDirName(target_file_path) == "" else getFileDirName(target_file_path))
    while True:
        outputFileName = validateFileName(target_file_path)
        working_dir = validateWorkingDirectory(getFileFullPath(folder_path, outputFileName))
        break

    return getFileFullPath(working_dir, outputFileName)


def displaySuccessfulMerge(outputFileName):
    print(Panel(f"""
File name: [i]{getFileBaseName(outputFileName)}[/i]
Folder: [i]{workingDir if getFileDirName(outputFileName) == "" else getFileDirName(outputFileName)}[/i]
""", title="MERGE COMPLETED", border_style="green", expand=False))


def deleteTemporaryCreatedFolder(savingFileFolder):
    # Allow user to delete their newly-created saving directory
    # Since we created this during process, we can delete it before the program ends
    if not (workingDir == savingFileFolder): 
        try:
            print(f"Deleted temporary directory ({savingFileFolder})....")
            os.rmdir(savingFileFolder)
        except Exception as e:
            print(f"[red]Error deleting temporary directory: {e} \nTarget path:{savingFileFolder}[/red]")


def displayMergeOverview(itemsList, outputFileName, savingFileFolder, preserveFiles, sort):
    """
    Overview of the entire task before the start of the job
    """
    fileSize = 0
    table = Table(show_header=False, show_lines=True, highlight=True)
    ordered_file_list_view = f"{"\n".join(f"{index+1}. ITEM: [blue]{getFileBaseName(item)}[/blue] | DIRECTORY: [yellow]{getFileDirName(item)}[/yellow]" for index, item in enumerate(itemsList))}"

    # Calculate estimated size of the merge
    for i in itemsList: fileSize += os.path.getsize(i) / (1024 * 1024)
    table.add_row("[bold][u]Files to be merged[/u][/bold]:\n(as merge order)", ordered_file_list_view)
    table.add_row("[bold][u]Output file[/u][/bold]:" , f"[i]{getFileBaseName(outputFileName)}[/i]")
    table.add_row("[bold][u]Saving directory[/u][/bold]:", f"[italic yellow]{savingFileFolder}[italic yellow]")
    table.add_row("[bold][u]Sort Order Mode (Optional)", f"{sort} ([i]{"No active sorting" if sort == None else sort.description() }[/i]) ")
    table.add_row("[bold][u]Estimated Size[/u][/bold]:", f">{fileSize: .2f} MB")
    print(Panel(table, subtitle="[i]MERGING OVERVIEW[/i]", border_style="blue", expand=False))

    # Warn user of immediate deletion if preserve is off
    if not preserveFiles: print("[underline bold red]ACTIONS CAUTION! Preserving of files is OFF. Original merging files will be deleted after merging![/underline bold red]")


def generateMergedPdfs(itemsList, outputFileName, preserveFiles):
    """
    This handles the main pdf merging.
    pdf files are accepted from list
    """
    try:
        doc = fitz.open()
        for file in itemsList:
            doc.insert_file(file)
            # Remove files if preserve is removed
            if not preserveFiles:
                os.remove(file)
        doc.save(outputFileName)
        displaySuccessfulMerge(outputFileName) # Print success

    # If output directory specified doesn't exist
    except Exception as e:  raise typer.BadParameter(f"Error. \n{e}")
    except FileNotFoundError: raise typer.BadParameter(f"Error: File not found for merging!!")


def mergeRuntime(itemsList, outputFileName, preserveFiles, sort):
    savingFileFolder = workingDir if getFileDirName(outputFileName) == "" else getFileDirName(outputFileName)
    print(getFileBaseName(outputFileName))

    displayMergeOverview(itemsList, outputFileName, savingFileFolder ,preserveFiles, sort)
    if typer.confirm("\nContinue with these settings?"): 
        generateMergedPdfs(itemsList, outputFileName, preserveFiles)
    else: 
        deleteTemporaryCreatedFolder(savingFileFolder)
        raise typer.Abort()


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
    #TODO: The following if/else statemetns are bad! Fix them.
    if validate:
        mergeFileList = validateListForPDF(items, exclude, mimecheck)
        # if outputFileName or filepath is not default then it will trigger its validation process
        outputFileName = validateOutputFileName(output) if (output != "merged.pdf" and not os.path.exists(output)) else "merged.pdf"
        
    else:
        mergeFileList, outputFileName = items, "merged.pdf"

    print(outputFileName, output)

    # If user passes a sort order, update the previous list
    # Needs to happen after validated list
    if sort: mergeFileList = sortList(sort, mergeFileList)
    print(output)
    print(outputFileName)
    mergeRuntime(mergeFileList, outputFileName, preserve, sort)
