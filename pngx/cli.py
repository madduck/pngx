#!/usr/bin/env python3

import sys
import click
import pathlib

from pngx.config import Config
from pngx.pngx import PaperlessNGX
from pngx.asyncio import asyncio_run

from .logger import get_logger, adjust_log_level


@click.group()
@click.option("--url", "-U", help="URL to the Paperless NGX instance")
@click.option("--token", "-T", help="API token for Paperless NGX instance")
@click.option(
    "--config",
    "-c",
    help="Config file to read",
    type=click.Path(path_type=pathlib.Path),
)
@click.option(
    "--verbose", "-v", count=True, help="Increase verbosity of log output"
)
@click.option(
    "--quiet", "-q", is_flag=True, help="Increase verbosity of log output"
)
@click.pass_context
def cli_base(ctx, verbose, quiet, url=None, token=None, config=None):
    """A command-line interface for Paperless NGX"""
    logger = get_logger(__name__)
    adjust_log_level(logger, verbose, quiet=quiet)

    cfg = Config(config)
    if url:
        cfg.set("url", url)
    if token:
        cfg.set("token", token)

    ctx.obj = ctx.with_resource(PaperlessNGX(config=cfg, logger=logger))


@cli_base.command()
@click.option("--owner", "-o", help="Owner for uploaded documents")
@click.option(
    "--group",
    "-g",
    "groups",
    multiple=True,
    help="Groups for uploaded documents",
)
@click.option(
    "--correspondent",
    "-c",
    help="Correspondent for uploaded documents",
)
@click.option(
    "--correspondent-must-exist",
    is_flag=True,
    help=(
        "Correspondent will not be created, but an error produced "
        "if correspondent does not exist"
    ),
)
@click.option(
    "--tag",
    "-t",
    "tags",
    multiple=True,
    help="Tags to assign to the documents",
)
@click.option(
    "--tags-must-exist",
    is_flag=True,
    help=(
        "Tags will not be created, but an error produced "
        "if a tag does not exist"
    ),
)
@click.option(
    "--replace-with-spaces",
    "spacereplaces",
    multiple=True,
    default=["_"],
    help="Characters in filenames to replace with spaces",
)
@click.option(
    "--datere",
    "dateres",
    multiple=True,
    default=[
        r"^(?:.*/)?(?P<date>\d{4}[-.]\d{2}[-.]\d{2})[-.]?(?P<remainder>.*)$"
    ],
    help="Python regular expressions to extract date and remainder groups",
)
@click.option(
    "--tries",
    type=click.IntRange(min=1),
    default=3,
    help="Retry this many times to upload documents",
)
@click.argument("filenames", type=click.Path(path_type=pathlib.Path), nargs=-1)
@click.pass_obj
@asyncio_run
async def upload(
    pngx,
    filenames,
    owner,
    groups,
    correspondent,
    correspondent_must_exist,
    tags,
    tags_must_exist,
    spacereplaces,
    dateres,
    nameres,
    tries,
):
    """Upload files to Paperless NGX"""

    for setting in ("tags_must_exist", "correspondent_must_exist", "tries"):
        if locals()[setting] is not None:
            pngx.config.set(f"upload.{setting}", locals()[setting])

    for listsetting in ("spacereplaces", "dateres", "nameres", "tags"):
        pngx.config.set(
            f"upload.{listsetting}",
            pngx.config.get(f"upload.{listsetting}", [])
            + locals()[listsetting],
        )

    try:
        async with pngx.connect():
            await pngx.upload(filenames, owner=owner, groups=groups, tags=tags)

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err))


@cli_base.group()
@click.pass_obj
@asyncio_run
async def tags(pngx):
    """Commands to manipulate tags in Paperless NGX"""


@tags.command()
@click.option(
    "--zero",
    "-0",
    is_flag=True,
    help="Use zero-delimiter instead of newlines",
)
@click.pass_obj
@asyncio_run
async def list(pngx, zero):
    """List the available tags in Paperless NGX"""
    try:
        async with pngx.connect():
            tags = await pngx.tags()
            click.echo(("\0" if zero else "\n").join(sorted(tags.keys())))

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err))


def main():
    return cli_base()


if __name__ == "__main__":
    sys.exit(main())
