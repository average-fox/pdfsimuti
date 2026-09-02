# Introduction

**Portable Document Format Simple Utility Tool** or pronounced as `pdfSimUti` (pdfsimuti on CMD) is a command-line simple tool created for mundane tasks involving PDF files. It is written in python with `Rich` colorful display, `Typer + Click` for terminal interface & `Magic` for file checking. It utilizes [PyMuPDF](https://github.com/pymupdf/PyMuPDF) and [GhostScript](https://www.ghostscript.com/about/index.html) for PDF file manipulation.

# Features
As of `v0.3.5` and beyond, `pdfSimUti` can do these tasks ~

1. Ability to merge files or compress them while providing options to change their behavior.

2. It can perform said abilities from file paths and `.txt` format files while excluding files from merging as well.

3. It can read an entire directory for PDF files (not recursively yet) as well.

4. `pdfSimUti` can perform said abilities while displaying an overview of the task and showing progress of the active task.

5. It can detect corrupted, password-protected or permission lacking files too.

6. It can sort out the files both by name, by creation date, by modified dates or none. Just add them in any order you like.

7. `pdfSimUti` has several exceptions built into it to handle most of the common issues if they arise on runtime.

8. It is cross platform supported by running on Windows operating systems and Linux distros. However, it has received no testing on MacOS so be cautious.

# Installation

`pdfSimUti` is not complete. So you won't find it on `PyPl` or any official sources. You can only install it using `uv`. 

1. Get `uv` installed on your machine first.
    ```
    # get uv
    (MacOS & Linux) curl -LsSf https://astral.sh/uv/install.sh | less
    (Windows) powershell -c "irm https://astral.sh/uv/install.ps1 | more"
    ```
2. Clone this repository in a preferred folder and nagivate to it.
    ```
    git clone https://github.com/average-fox/pdfsimuti
    ```
3. Install it via `uv`. I suggest that you use a virtual environment first.
    ```
    uv pip install .
    ```

    Due to `pdfsimUti` being quite untested (yet!), i suggest that you run it with a virtual environmental (`venv`) first.
4. Check installation status
    ```
    pdfsimuti --version
    ```

Sidenote: `pdfSimUti` requires `Python 3.13.5` installed on your machine. With new Python versions, the program attempts to incorporate new features and optimizations. The same applies to its dependencies.
# Development

`pdfSimUti` is a hobby project of mine created for merging files or compressing them without any *specialized software app* or any reliance from internet saying `Daily File Size Exceeded`. It is far from complete and miss a lot of features.

It is written without any AI assistance and only tested by me. I appreciate your suggestions towards `pdfSimUti` and suggest to report any [issues](https://github.com/average-fox/pdfsimuti/issues) with the program on GitHub. 