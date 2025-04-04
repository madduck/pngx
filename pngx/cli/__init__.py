#!/usr/bin/env python3

import sys
import click
import pathlib

from pngx.config import Config, merge_cli_opts_into_cfg
from pngx.logger import get_logger, adjust_log_level
from pngx.pngx import PaperlessNGX

from .tags import tags
from .upload import upload


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
def cli(
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


cli.add_command(tags)
cli.add_command(upload)


def main():
    return cli()


if __name__ == "__main__":
    sys.exit(main())
