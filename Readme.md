<p align="center">
    <img src="https://github.com/average-fox/assets/blob/main/pdfsimuti/demo.png?raw=true" alt="pdfsimuti demo" width="78%">
</p>

**Portable Document Format Simple Utility Tool** or pronounced as `pdfSimUti` (pdfsimuti on the CLI) is a simple Command Line Interface (CLI) software created for mundane tasks involving PDF files. It is written in python with `Rich` for colorful terminal display and `Typer + Click` for terminal interface. It utilizes [PyMuPDF](https://github.com/pymupdf/PyMuPDF) for PDF file manipulation and supports [GhostScript](https://www.ghostscript.com/about/index.html) for advanced compression as well.

## Features
As of `v0.3.5`, `pdfSimUti` can~

1. Merge files or compress them.

2. It can perform operations from file paths and `.txt` format files while also specifying which files to ignore/exclude.

3. It can read an entire directory for PDF files (not recursively yet) as well by passing `.`

4. `pdfSimUti` displays an overview of the task and showing progress of the active task.

5. It can detect corrupted, password-protected or files with lack of permission.

6. It can sort out the files both by name, by creation date, by modified dates or none. Just add them in any order you like.

7. `pdfSimUti` has several exceptions built into it to handle most of the common issues if they arise at runtime. If an invalid filename, an output location or invalid command is detected; `pdfsimuti` will stop until it is resolved and continue it's operation.

8. It is cross-platform compatible. It can run on Windows OS (10,11) and Linux distros. ***However***, it has received no testings on MacOS so be cautious.

## Installation

`pdfSimUti` is not complete so you won't find it on `PyPl` or any official sources. You can only install it from this repository using `uv`.

1. Get `uv` installed on your machine first.

    * MacOS or Linux

        ```
        curl -LsSf https://astral.sh/uv/install.sh | less
        ```
    
    * Windows

        ```
        powershell -c "irm https://astral.sh/uv/install.ps1 | more"
        ```

2. Clone this repository in a preferred folder and navigate to it.
    ```
    git clone https://github.com/average-fox/pdfsimuti
    cd pdfsimuti
    ```
3. Install it via `uv`
    ```
    uv pip install . --system
    ```

    This will install the software on your entire machine. If you wish to use it in a virtual environmnent,
        
        uv venv
        uv pip install .
    

4. Check installation status
    ```
    pdfsimuti --version
    ```

Sidenote: `pdfSimUti` requires `Python 3.13.5` (or better) installed on your machine. With new Python versions comes newer features and optimizations. The same applies to its dependencies.
## Development

`pdfSimUti` is a hobby project of mine created for merging files or compressing them without any *specialized software app*. It is far from complete and is missing many features. But of `v0.3.5` and beyond, it is ready for use. 

It is written without any AI assistance and only tested by me. I appreciate your suggestions for `pdfSimUti` and recommend to report any [issues](https://github.com/average-fox/pdfsimuti/issues) with the program on GitHub. 