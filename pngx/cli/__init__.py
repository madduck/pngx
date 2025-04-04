#!/usr/bin/env python3

import sys
import click

from pngx.config import (
    config_file_option,
    merge_config,
)
from pngx.logger import get_logger, log_level_from_cli
from pngx.pngx import PaperlessNGX

from .tags import tags
from .upload import upload

Unspecified = object()


@click.group
@config_file_option
@merge_config
@click.option("--url", "-U", help="URL to the Paperless NGX instance")
@click.option("--token", "-T", help="API token for Paperless NGX instance")
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
def pngx(
    ctx,
    config,
    url,
    token,
    no_act,
    verbose,
    quiet,
):
    """A command-line interface for Paperless NGX"""
    if no_act and verbose <= 1:
        verbose = 1

    # set up the base logger;
    # even if we don't need it, it is the basis for sub loggers
    logger = get_logger()
    log_level_from_cli(logger, verbose, quiet=quiet)

    ctx.obj = ctx.with_resource(
        PaperlessNGX(url=url, token=token, no_act=no_act)
    )


pngx.add_command(tags)
pngx.add_command(upload)


def main():
    return pngx()


if __name__ == "__main__":
    sys.exit(main())
