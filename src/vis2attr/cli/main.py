"""Main CLI entry point for vis2attr."""

import click
from .analyze import analyze_command
from .report import report_command


@click.group()
@click.version_option()
def main():
    """vis2attr: Visual Language Model for Attribute Extraction
    
    Turn item photos into structured attributes using VLMs.
    """
    pass


# Add subcommands
main.add_command(analyze_command)
main.add_command(report_command)


if __name__ == "__main__":
    main()
