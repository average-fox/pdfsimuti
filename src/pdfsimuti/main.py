import typer
import importlib
import importlib.metadata

from typing import Optional, Annotated
from click import Context
from click.core import Command

__version__ = importlib.metadata.version('pdfsimuti')

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False, suggest_commands = True,
    context_settings={"help_option_names" : ["-h", "--help"]},)

class customTyperGroup(typer.core.TyperGroup):
    def __init__(self, commands: None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.commands = {
            "merge": "pdfsimuti.features.merge",
            "compress": "pdfsimuti.features.compress"
        }


    def list_commands(self, ctx: Context) -> list[str]:
        return super().list_commands(ctx) + self.commands.keys()


    def get_command(self, ctx: Context, command_name: str) -> Command | None:
        if command_name in self.commands:
            command = self._lazy_load(command_name)
            command.info.name = command_name
            return typer.main.get_command(command)

        return super().get_command(ctx, command_name)


    def _lazy_load(self, command_name: str) -> typer.Typer:
        module_name = self.commands[command_name]
        module = importlib.import_module(module_name)
        app_object = getattr(module, "app", None)
        if not app_object: raise ValueError(f"Lazy loading {module_name} failed.")

        return app_object


def version_callback(value:bool):
    if value:
        print(f"pdfSimUti v{__version__}")
        raise typer.Exit()


@app.callback(epilog="Author: average-fox (@foxes_nteq_dogs)", cls=customTyperGroup)
def main(version: Annotated[
    Optional[bool],
    typer.Option("--version", "-v", callback=version_callback, is_eager=True, help="Show version & exit")] = None,
    ):
    """
    Utility collection tool for PDF written in Python with Typer.
    """
    pass


if __name__ == "__main__": app()