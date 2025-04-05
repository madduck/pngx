import asyncio
import aiohttp
from aiofile import async_open
import contextlib
import re

import random
from pypaperless import Paperless
import pypaperless.exceptions
from pypaperless.models.common import (
    MatchingAlgorithmType,
    PermissionSetType,
    PermissionTableType,
)

from pngx.wrapper import PaperlessObjectWrapper


class PaperlessNGX:

    class Exception(RuntimeError):
        pass

    class MissingConfigError(Exception):
        def __init__(self, arg):
            super().__init__(f"No {arg} specified, and none in config")

    class MissingObjectError(Exception):
        pass

    def __init__(self, *, url, token, logger, no_act=False):
        self._logger = logger
        self._timeout = aiohttp.ClientTimeout(
            connect=30, sock_connect=30, sock_read=120
        )
        self._url = url
        self._token = token
        self._no_act = no_act
        self._api = None
        self._api_users = None
        self._api_groups = None
        self._api_tags = None
        self._api_doctypes = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_info, exc_tb):
        pass

    @contextlib.asynccontextmanager
    async def connect(self, *, url=None, token=None):

        url = url or self._url
        if not url:
            raise self.MissingConfigError("URL")
        token = token or self._token
        if not token:
            raise self.MissingConfigError("API token")

        async with contextlib.AsyncExitStack() as stack:
            session = await stack.enter_async_context(
                aiohttp.ClientSession(timeout=self._timeout)
            )
            self._api = await stack.enter_async_context(
                Paperless(url, token, session=session)
            )
            self._api_users = PaperlessObjectWrapper(
                self._api.users, namecol="username"
            )
            self._api_groups = PaperlessObjectWrapper(self._api.groups)
            self._api_tags = PaperlessObjectWrapper(self._api.tags)
            self._api_correspondents = PaperlessObjectWrapper(
                self._api.correspondents
            )
            self._api_doctypes = PaperlessObjectWrapper(
                self._api.document_types
            )

            yield self

        self._api = None
        self._api_users = None
        self._api_groups = None
        self._api_tags = None
        self._api_correspondents = None
        self._api_doctypes = None

    async def _get_user_id_by_name(self, username, **args):
        return await self._api_users.get_id_by_name(username, **args)

    async def _get_group_id_by_name(self, groupname, **args):
        return await self._api_groups.get_id_by_name(groupname, **args)

    async def _get_tag_id_by_name(self, tagname, **args):
        return await self._api_tags.get_id_by_name(tagname, **args)

    async def _get_correspondent_id_by_name(self, correspondent, **args):
        return await self._api_correspondents.get_id_by_name(
            correspondent, **args
        )

    async def _get_doctype_id_by_name(self, doctype, **args):
        return await self._api_doctypes.get_id_by_name(doctype, **args)

    async def _make_permission_table(self, groups):
        if groups:
            return PermissionTableType(
                view=PermissionSetType(
                    groups=[],
                ),
                change=PermissionSetType(
                    groups=[
                        await self._get_group_id_by_name(g) for g in groups
                    ],
                ),
            )

        return PermissionTableType()

    async def _get_or_make_tags(
        self,
        tags,
        *,
        owner,
        groups,
        make=True,
        is_inbox_tag=False,
        is_insensitive=True,
        match="",
        matching_algorithm=MatchingAlgorithmType.NONE,
        color="#%06x" % random.randint(0, 2**24),
    ):
        perms = await self._make_permission_table(groups)
        ret = []
        for t in tags:
            try:
                ret.append(
                    await self._get_tag_id_by_name(
                        t,
                        make=make,
                        make_args=dict(
                            is_inbox_tag=is_inbox_tag,
                            is_insensitive=is_insensitive,
                            match=match,
                            matching_algorithm=matching_algorithm,
                            color=color,
                        ),
                        permissions_table=perms,
                        owner=(
                            await self._get_user_id_by_name(owner)
                            if owner
                            else None
                        ),
                    )
                )

            except KeyError:
                raise self.MissingObjectError(
                    f"Tag '{t}' does not exist "
                    "(and upload.tags_must_exist is set)"
                )

        return ret

    async def _get_or_make_correspondent(
        self,
        correspondent,
        *,
        owner,
        groups,
        make=True,
        is_insensitive=True,
        match="",
        matching_algorithm=MatchingAlgorithmType.AUTO,
        color="#%06x" % random.randint(0, 2**24),
    ):
        perms = await self._make_permission_table(groups)
        try:
            return await self._get_correspondent_id_by_name(
                correspondent,
                make=make,
                make_args=dict(
                    match=match,
                    is_insensitive=is_insensitive,
                    matching_algorithm=matching_algorithm,
                    color=color,
                ),
                permissions_table=perms,
                owner=(
                    await self._get_user_id_by_name(owner) if owner else None
                ),
            )

        except KeyError:
            raise self.MissingObjectError(
                f"Correspondent '{correspondent}' does not exist "
                "(and upload.correspondent_must_exist is set)"
            )

    async def upload(
        self,
        filenames,
        *,
        owner=None,
        groups=None,
        correspondent=None,
        correspondent_must_exist=None,
        tags=None,
        tags_must_exist=None,
        dateres=None,
        nameres=None,
        tries=1,
    ):
        if not filenames:
            return

        if self._api is None:
            raise RuntimeError("API is not connected")

        try:
            tags = await self._get_or_make_tags(
                tags,
                make=not tags_must_exist and not self._no_act,
                owner=owner,
                groups=groups,
            )

        except self.MissingObjectError:
            if self._no_act and not tags_must_exist:
                logger.info(f"Would try to create tags: {tags}")
            else:
                raise

        if correspondent:
            try:
                _correspondent = await self._get_or_make_correspondent(
                    correspondent,
                    make=not correspondent_must_exist and not self._no_act,
                    owner=owner,
                    groups=groups,
                )
                if not self._no_act:
                    correspondent = _correspondent

            except self.MissingObjectError:
                if self._no_act and not correspondent_must_exist:
                    logger.info(
                        f"Would try to create correspondent: {correspondent}"
                    )
                else:
                    raise

        try:
            return await asyncio.gather(
                *[
                    self._upload_single(
                        file,
                        owner=owner,
                        groups=groups,
                        tags=tags,
                        correspondent=correspondent,
                        dateres=dateres,
                        nameres=nameres,
                    )
                    for file in filenames
                ]
            )

        except aiohttp.client_exceptions.ClientResponseError as err:
            self._logger.error(f"API request denied: {err}")

        return None

    def _make_title(self, filename, nameres):

        for rgx in nameres or []:

            if rgx[0] == "s":
                delim = rgx[1]
                parts = rgx.split(delim)
                if len(parts) not in (3, 4):
                    self._logger.error(f"Invalid regular expression: {rgx}")
                    continue

                res = re.sub(parts[1], parts[2], filename)
                self._logger.debug(f"namere: {filename} ~= {rgx} → {res}")
                filename = res

            else:
                self._logger.error(
                    f"Regular expression must start with 's': {rgx}"
                )
                continue

        return filename

    @staticmethod
    def _get_creation_date(filename, dateres):
        for rgx in dateres:
            m = re.match(rgx, filename)
            if not m:
                continue

            matchdict = m.groupdict()

            if ret := matchdict.get("date"):
                return ret, matchdict.get("remainder", filename)

        return None, filename

    async def _upload_single(
        self,
        file,
        *,
        owner,
        groups,
        tags,
        correspondent,
        dateres=None,
        nameres=None,
        tries=1,
    ):
        filename = str(file.stem)
        if dateres:
            creationdate, filename = self._get_creation_date(filename, dateres)
            if creationdate:
                self._logger.debug(
                    f"Extracted date {creationdate} from filename {file}"
                )
            else:
                self._logger.debug(
                    f"Failed to extract date from filename {file}"
                )
        else:
            creationdate = None

        title = self._make_title(filename or str(file.stem), nameres)

        self._logger.debug(f"Title extracted from {file}: {title}")

        async def _do_upload(**kwargs):
            if self._no_act:
                self._logger.info(f"Would upload file {file}:")
                del kwargs["filename"]
                for k, v in kwargs.items():
                    if v is not None and v != []:
                        self._logger.info(f"  {k}: {v}")
                return None
            else:
                async with async_open(file, "rb") as f:
                    draft = self._api.documents.draft(
                        document=await f.read(), **kwargs
                    )
                    taskid = await draft.save()
                self._logger.info(f"File {file} uploaded, task ID {taskid}")
                return taskid

        try:
            return await _do_upload(
                filename=file.name,
                title=title,
                tags=tags,
                correspondent=correspondent,
                created=creationdate,
            )

        except aiohttp.client_exceptions.ServerTimeoutError as err:
            self._logger.warning(
                "Connection problem during upload " f"of file {file}: {err}"
            )

        except pypaperless.exceptions.BadJsonResponseError as err:
            self._logger.warning(
                "Paperless reported an error with the upload "
                f"of file {file}: {err}"
            )

        except FileNotFoundError as err:
            self._logger.error(f"File not found: {err.filename}")
            return

        except Exception as err:
            self._logger.exception(
                "Received other exception during upload "
                f"of file {file}: {err}"
            )

        if (tries := tries - 1) > 0:
            self._logger.info(
                f"Upload of {file} failed, " f"retrying {tries} time(s)…"
            )
            await asyncio.sleep(1)
            return await self._upload_single(
                file,
                owner=owner,
                groups=groups,
                tags=tags,
                dateres=dateres,
                nameres=nameres,
                tries=tries,
            )

        else:
            self._logger.error(f"Upload of {file} failed all retries.")
            return

    async def tags(self):
        return await self._api_tags.get_all()
