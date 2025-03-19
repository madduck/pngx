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
    "--tag",
    "-t",
    "tags",
    multiple=True,
    help="Tags to assign to the documents",
)
@click.option(
    "--tags-must-exist",
    "-x",
    is_flag=True,
    help="Tags will not be created, but an error produced if a tag does not exist",
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
        r"^(?:.*/)?(?P<date>\d{4}[-.]\d{2}[-.]\d{2})[-.](?P<remainder>.*)$"
    ],
    help="Python regular expressions to extract date",
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
    tags,
    tags_must_exist,
    spacereplaces,
    dateres,
    tries,
):
    tags_must_exist = tags_must_exist or pngx.config.get(
        "upload.tags_must_exist"
    )

    try:
        async with pngx.connect():
            await pngx.upload(
                filenames,
                owner=owner,
                groups=groups,
                tags=tags,
                tags_must_exist=tags_must_exist,
                spacereplaces=spacereplaces,
                dateres=dateres,
                tries=tries,
            )

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err))


@cli_base.group()
@click.pass_obj
@asyncio_run
async def tags(pngx):
    pass


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
