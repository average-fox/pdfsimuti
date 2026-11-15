from typing import List, Optional, Annotated
from pathlib import Path
from enum import Enum

import typer

app = typer.Typer(rich_markup_mode = "rich", pretty_exceptions_show_locals=False)
CURRENT_DIR = Path.cwd()

#TODO: change os.getcwd() with Path.cwd() on all features

class convert_select_mode(str, Enum):
    image =  "image_2_pdf"
    pdf = "pdf_2_image"


class convert_select_format(str, Enum):
    jpg = "jpg"

session_job:dict = {
    "mode": None,
    "format": None,
    "target_file": None,
    "output": None,
}

def designate_output(session_job:dict):
    while True:
        match session_job['mode']:

            case subject if (subject == "image_2_pdf" and session_job["output"].is_dir() and session_job["output"] != CURRENT_DIR):
                print("Output needs to be directory for converting Image to PDF.")
                session_job["output"] = Path(typer.prompt("Enter new output location (directory): "))

            case subject if (subject == "pdf_2_image" and session_job["output"].is_dir() and session_job["output"] != CURRENT_DIR):
                print("Output needs to be directory for converting Image to PDF.")
                session_job["output"] = Path(typer.prompt("Enter new output location (directory): "))
            case _:
                break     


def validate_job(session_job:dict) -> bool:
    return True

# there will be either image or PDF
# for the alpha, I recommend just trying to convert to a single image format like JPG

## for the sake of the converting and all the other stuff, it is better to make sure that target is actually a list alongside the target file.
## this will be easy to make and if pdf are being converted to image then separate folders can be created for that.


@app.command(help="""
Convert between PDF and IMAGE files
"""
)

def convert(
    mode: Annotated[convert_select_mode, typer.Option("--mode", "-m", case_sensitive=False, help="Set mode of convert.", rich_help_panel="Mandatory")],
    format: Annotated[convert_select_format, typer.Option("--format", "-f", case_sensitive=False, help="Set mode of convert.", rich_help_panel="Mandatory")] = convert_select_format.jpg,
    target: Annotated[List[Path], typer.Argument(help="File to convert. Either PDF or Image")]=[],
    output: Annotated[List[Path], typer.Option("--output", "-o",case_sensitive=False, help="Specify conversion output path.", rich_help_panel="Options")] = [CURRENT_DIR]
):
    print(mode)
    print(format)
    print(target)
    print(output)