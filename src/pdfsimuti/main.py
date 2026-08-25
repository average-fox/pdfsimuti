import typer
import importlib
import importlib.metadata

from typing import Optional, Annotated
from click import Context
from click.core import Command

from typer.core import TyperGroup

__version__ = importlib.metadata.version('pdfsimuti')

app = typer.Typer(
    no_args_is_help=True, pretty_exceptions_show_locals=False, rich_markup_mode="rich", add_completion=False, suggest_commands = True,
    context_settings={"help_option_names" : ["-h", "--help"]},)


class customTyperGroup(TyperGroup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lazyCommands = {
        "merge": "pdfsimuti.features.merge",
        "compress": "pdfsimuti.features.compress",
        "checkhealth": "pdfsimuti.diagnostic.checkhealth"
        }


    def list_commands(self, ctx: Context) -> list[str]:
        return super().list_commands(ctx) + list(self.lazyCommands.keys())


    def get_command(self, ctx: Context, cmd_name: str) -> Command | None:
        if cmd_name in self.lazyCommands:
            cmd = self._lazy_load(cmd_name)
            cmd.info.name = cmd_name
            return typer.main.get_command(cmd)
        return super().get_command(ctx, cmd_name)


    def _lazy_load(self, command_name: str) -> typer.Typer:
        module_name = self.lazyCommands[command_name]
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