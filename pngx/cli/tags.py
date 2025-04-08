import click

from pngx.asyncio import asyncio_run
from pngx.pngx import PaperlessNGX


@click.group()
@click.pass_obj
@asyncio_run
async def tags(pngx: PaperlessNGX) -> None:
    """Commands to manipulate tags in Paperless NGX"""


@tags.command(name="list")
@click.option(
    "--zero/--nl",
    "-0/-n",
    is_flag=True,
    help="Use zero-delimiter instead of newlines",
)
@click.option(
    "--ids/--no-ids",
    is_flag=True,
    help="Include the tag IDs in the output",
)
@click.pass_obj
@asyncio_run
async def taglist(pngx: PaperlessNGX, zero: bool, ids: bool) -> None:
    """List the available tags in Paperless NGX"""
    try:
        async with pngx.connect():
            tags = await pngx.tags()
            if ids:
                tags_list = [f"{tag} ({id})" for tag, id in tags.items()]
            else:
                tags_list = list(tags.keys())
            click.echo(("\0" if zero else "\n").join(sorted(tags_list)))

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err)) from err
