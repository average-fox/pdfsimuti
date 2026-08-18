import sys
import shutil # used for getting ghostscriptapplication PATH variables
import subprocess # capture output

import importlib.util # getting package ModuleSpec
from importlib.metadata import version # for checking packages versions



from typing import TypedDict

class packageInfo(TypedDict):
    version: str | None
    searchLoc: str | None
    installed: str
    description: str


packages_dict:dict[str, packageInfo] = {
    'pymupdf' : {
        "version": None, 
        "searchLoc": None, 
        "installed": "[red]Not installed[/red]",
        "description" : """
        [u][b]Description[/b][/u]: 
        Used as the main package for merging the files. Also have features to provide simple compressions.
        """},
    
    'magic' : {
        "version": None, 
        "searchLoc": None, 
        "installed": "[red]Not installed[/red]",
        "description": """
        [u][b]Description[/b][/u]
        Used for checking if the file is actually the file format it claims to be. It checks for their mimecheck type.
        Without this, you cannot do something like the following~
        [code]pdfsimuti merge --no-mimecheck FILE1.pdf FILE2.pdf[/code]
        """},
    
    "ghostscript" : {
        "version": None,
        "searchLoc": None,
        "installed": "[red]Not installed[/red]",
        "description": f"""
        [u][b]Description[/b][/u]: 
        GhostScript is a interpreter for PostScript and PDF. pdfSimUti doesn't install GhostScript because it's setup is different.
        Should you choose to compress PDF files using GhostScript
        instead of the default compression by "PyMuPDF", complete the setup below~
        
        [b][u]Installation[/u][/b]
        1. Go to [link=https://ghostscript.com/releases/gsdnld.html]gsdnld.html[/link] and download your ghostscript package
        2. Install your GhostScript package. 
        3. If you're on Windows, be sure to add your ghostscript package's "bin" directory to your PATH environments.
        
        [b][u]Verification[/u][/b]
        1. If you are on windows, run [code]gswin64c[/code] ([i]assuming you're on 64 bit[/i])
        2. If you are on linux, run [code]gs[/code] 
        3. If you are on something else, [link=https://github.com/foxtbirdy/PDFsimuti/issues/new]open an issue[/link]
        4. If you have done 1 & 2 and checkhealth  responds with "[i]Not Found[/i]", [link=https://github.com/foxtbirdy/PDFsimuti/issues/new]open an issue[/link]
        """
        }    
}


def get_gs_detail():
    """
    Get ghostscript details on your system.
    1. figure out what ghostscript you installed without telling you by figuring out your os and architecture
    2. calls subprocess to capture ghostscript version and other info
    3. calls shutil to locate ghostscript installed path
    4. updates 'packages_dict' for checkhealth feature
    
    if not found, nothing happens.
    """
    from pdfsimuti.utils import rtn_gs_name

    gs_name = rtn_gs_name()
    try: 
        result = subprocess.run([gs_name, '--version'], capture_output=True, text=True)
    except FileNotFoundError: return 0
    
    if result.stdout:
        bin_loc = shutil.which(gs_name) # get location of the package
        packages_dict["ghostscript"]["version"] = result.stdout.rstrip() # rstrip gets rid of the /n that comes from the capture_output
        packages_dict["ghostscript"]["searchLoc"] = bin_loc
        packages_dict["ghostscript"]["installed"] = "[green]Installed[/green]"
    

def update_packages_dict(*args):
    """
    Update 'packages_dict' of their moduleSpec, installed location and other info.
    """

    # Note: magic in importlib.util.find_spec is not a valid name for importlib.metadata.version
    ## therefore, it's name is processed as either 'python-magic' or 'python-magic-bin' after find_spec
    for package, item in packages_dict.items():
        if package not in args:
            pass
        
        spec = importlib.util.find_spec(package)
        if package == "magic" and spec != None: item["version"] = version('python-magic-bin' if sys.platform == "win32" else 'python-magic')
        # whoever decided magic should have different package names should be hanged.
        # this code is important because importlib.util and importlib.metadata.version are not the same!  
        
        if spec:
            if not item["version"]: item["version"] = version(package)
            item["searchLoc"] = (spec.submodule_search_locations or [""])[0]
            item["installed"] = "[green]Installed[/green]"


def checkhealth_output():
    from rich.prompt import Prompt
    from rich.tree import Tree
    from rich.console import Console

    console = Console()
    package_tree = Tree("Package Status")

    update_packages_dict('pymupdf', 'magic')
    get_gs_detail()

    for package in packages_dict.items():
        pac = package_tree.add(package[0])
        pac.add("[u][b]Status: [/b][/u]" + package[1]["installed"])
        pac.add("[u][b]Version: [/b][/u]" + (package[1]["version"] or ""))
        pac.add("[u][b]Source: [/b][/u]" + (package[1]["searchLoc"] or "")) 

    with console.screen():
        console.print(package_tree)
        Prompt.ask("\nContinue?")



def checkhealth():
    # update_packages_dict('pymupdf', 'magic') # wrote this otherwise the code would have been ugly
    # get_gs_detail() # created only for ghostscript

    checkhealth_output()


    # match verbose:
    #     case 1: verbose_level_1()
    #     case 2: verbose_level_2()
    #     case 3: verbose_level_3()
