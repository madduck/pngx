import click
import pathlib

from pngx.config import merge_cli_opts_into_cfg
from pngx.asyncio import asyncio_run
from pngx.pngx import PaperlessNGX


@click.command()
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
