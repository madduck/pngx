#!/usr/bin/env python3

import sys
import click
import pathlib

from pngx.config import Config, merge_cli_opts_into_cfg
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
    "--no-act",
    "-n",
    is_flag=True,
    help=("Do not actually act, " "just show what would be done"),
)
@click.option(
    "--verbose",
    "-v",
    count=True,
    help="Increase verbosity of log output",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Increase verbosity of log output",
)
@click.pass_context
def cli_base(
    ctx,
    no_act,
    verbose,
    quiet,
    url,
    token,
    config,
):
    """A command-line interface for Paperless NGX"""
    explicit_cli_opts = {
        k: v
        for k, v in locals().items()
        if ctx.get_parameter_source(k)
        not in (
            click.core.ParameterSource.DEFAULT,
            click.core.ParameterSource.DEFAULT_MAP,
        )
    }
    cfg = Config(config)
    merge_cli_opts_into_cfg(
        explicit_cli_opts,
        cfg,
        exclude=("ctx", "cfg", "config", "verbose", "quiet"),
    )

    if no_act:
        if verbose <= 1:
            verbose = 1

    logger = get_logger(__name__)
    adjust_log_level(logger, verbose, quiet=quiet)

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
    "--correspondent-must-exist/--make-missing-correspondent",
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
    "--tags-must-exist/--make-missing-tags",
    help=(
        "Tags will not be created, but an error produced "
        "if a tag does not exist"
    ),
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
    "--namere",
    "nameres",
    multiple=True,
    help="Python regular expressions to manipulate document name",
)
@click.option(
    "--tries",
    type=click.IntRange(min=1),
    default=3,
    help="Retry this many times to upload documents",
)
@click.argument("filenames", type=click.Path(path_type=pathlib.Path), nargs=-1)
@click.pass_context
@asyncio_run
async def upload(
    ctx,
    filenames,
    owner,
    groups,
    correspondent,
    correspondent_must_exist,
    tags,
    tags_must_exist,
    dateres,
    nameres,
    tries,
):
    """Upload files to Paperless NGX"""
    explicit_cli_opts = {
        k: v
        for k, v in locals().items()
        if ctx.get_parameter_source(k)
        not in (
            click.core.ParameterSource.DEFAULT,
            click.core.ParameterSource.DEFAULT_MAP,
        )
    }
    pngx = ctx.obj
    merge_cli_opts_into_cfg(
        explicit_cli_opts, pngx.config, exclude=("pngx"), path="upload"
    )

    try:
        async with pngx.connect():
            await pngx.upload(filenames, owner=owner, groups=groups)

    except PaperlessNGX.Exception as err:
        raise click.UsageError(str(err))


@cli_base.group()
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


def main():
    return cli_base()


if __name__ == "__main__":
    sys.exit(main())
