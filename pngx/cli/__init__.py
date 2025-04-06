#!/usr/bin/env python3

import sys
import click
import click_extra as clickx
import logging
from yarl import URL

from pngx.pngx import PaperlessNGX

from .tags import tags
from .upload import upload


def validate_url(ctx, param, value):
    if value is not None:
        try:
            url = URL(value)
            if not url.is_absolute():
                raise click.BadParameter(f"URL is not absolute: {value}")
            return url

        except TypeError:
            raise click.BadParameter(
                f"URLs must be strings, not '{type(value).__name__}': {value}"
            )

        except ValueError:
            raise click.BadParameter(f"Not a valid URL: {value}")


logging.getLogger("click_extra").setLevel(logging.WARNING)
logger = clickx.new_extra_logger(
    format=("{asctime} {name} {levelname} {message} " "({filename}:{lineno})"),
    datefmt="%F %T",
    level=logging.WARNING,
)
logging.getLogger("asyncio").setLevel(logging.WARNING)


@click.group
@clickx.config_option(show_default=True)
# @clickx.verbosity_option(default_logger=logger)
@clickx.verbose_option(default_logger=logger)
@click.option(
    "--url",
    "-U",
    required=True,
    help="URL to the Paperless NGX instance",
    callback=validate_url,
)
@click.option("--token", "-T", help="API token for Paperless NGX instance")
@click.option(
    "--no-act",
    "-n",
    required=True,
    is_flag=True,
    help=("Do not actually act, " "just show what would be done"),
)
@click.pass_context
def pngx(
    ctx,
    url,
    token,
    no_act,
):
    """A command-line interface for Paperless NGX"""
    # if no_act and verbose <= 1:
    #    verbose = 1

    # set up the base logger;
    # even if we don't need it, it is the basis for sub loggers
    # logger = get_logger()
    # log_level_from_cli(logger, verbose, quiet=quiet)
    # silence_other_loggers(f"pypaperless[{url.host}]", "asyncio")
    logging.getLogger(f"pypaperless[{url.host}]").setLevel(logging.WARNING)

    ctx.obj = ctx.with_resource(
        PaperlessNGX(url=url, token=token, no_act=no_act)
    )


pngx.add_command(tags)
pngx.add_command(upload)


def main():
    return pngx()


if __name__ == "__main__":
    sys.exit(main())
