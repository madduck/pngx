import click

from pngx.asyncio import asyncio_run
from pngx.pngx import PaperlessNGX


@click.group()
@click.pass_obj
@asyncio_run
async def tags(pngx):
    """Commands to manipulate tags in Paperless NGX"""


@tags.command(name="list")
@click.option(
    "--zero",
    "-0",
    is_flag=True,
    help="Use zero-delimiter instead of newlines",
)
@click.pass_obj
@asyncio_run
async def taglist(pngx, zero):
    """List the available tags in Paperless NGX"""
    try:
        async with pngx.connect():
            tags = await pngx.tags()
            click.echo(("\0" if zero else "\n").join(sorted(tags.keys())))

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err))
