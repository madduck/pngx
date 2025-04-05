import click

from pngx.asyncio import asyncio_run
from pngx.pngx import PaperlessNGX
from pngx.config import merge_config


@click.group()
@click.pass_obj
@asyncio_run
async def tags(pngx):
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
@merge_config
@click.pass_obj
@asyncio_run
async def taglist(pngx, zero, ids):
    """List the available tags in Paperless NGX"""
    try:
        async with pngx.connect():
            tags = await pngx.tags()
            if ids:
                tags = [f"{tag} ({id})" for tag, id in tags.items()]
            else:
                tags = tags.keys()
            click.echo(("\0" if zero else "\n").join(sorted(tags)))

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err))
