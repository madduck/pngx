# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

import asyncio
import contextlib
import logging
import random
import re
from typing import TYPE_CHECKING

import aiohttp
import pypaperless.exceptions
from aiofile import async_open
from pypaperless import Paperless
from pypaperless.models.common import (
    MatchingAlgorithmType,
    PermissionSetType,
    PermissionTableType,
)
from yarl import URL

from pngx.wrapper import PaperlessObjectWrapper

if TYPE_CHECKING:
    import pathlib
    from collections.abc import AsyncGenerator
    from types import TracebackType
    from typing import Any, Literal, Type

    from pngx.wrapper import Cache

    BaseClass = contextlib.AbstractContextManager["PaperlessNGX"]
else:
    BaseClass = object


logger = logging.getLogger(__name__)


class PaperlessNGX(BaseClass):
    class Exception(RuntimeError):
        pass

    class APINotConnectedError(Exception):
        pass

    class MissingConfigError(Exception):
        def __init__(self, arg: str) -> None:
            super().__init__(f"No {arg} specified, and none in config")

    class MissingObjectError(Exception):
        pass

    def __init__(self, *, url: URL, token: str, no_act: bool = False) -> None:
        self._timeout = aiohttp.ClientTimeout(
            connect=30, sock_connect=30, sock_read=120
        )
        self._url = url
        self._token = token
        self._no_act = no_act
        self._api: Paperless | None = None
        self._api_users: PaperlessObjectWrapper | None = None
        self._api_groups: PaperlessObjectWrapper | None = None
        self._api_tags: PaperlessObjectWrapper | None = None
        self._api_correspondents: PaperlessObjectWrapper | None = None
        self._api_doctypes: PaperlessObjectWrapper | None = None

    def __enter__(self) -> PaperlessNGX:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Literal[False]:
        return False

    @contextlib.asynccontextmanager
    async def connect(
        self, *, url: URL | None = None, token: str | None = None
    ) -> AsyncGenerator[PaperlessNGX, None]:
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
            if self._api is None:
                raise self.APINotConnectedError

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

    async def _get_user_id_by_name(self, username: str, **args: Any) -> int:
        if self._api_users is not None:
            return await self._api_users.get_id_by_name(username, **args)
        raise self.APINotConnectedError

    async def _get_group_id_by_name(self, groupname: str, **args: Any) -> int:
        if self._api_groups is not None:
            return await self._api_groups.get_id_by_name(groupname, **args)
        raise self.APINotConnectedError

    async def _get_tag_id_by_name(self, tagname: str, **args: Any) -> int:
        if self._api_tags is not None:
            return await self._api_tags.get_id_by_name(tagname, **args)
        raise self.APINotConnectedError

    async def _get_correspondent_id_by_name(
        self, correspondent: str, **args: Any
    ) -> int:
        if self._api_correspondents is not None:
            return await self._api_correspondents.get_id_by_name(
                correspondent, **args
            )
        raise self.APINotConnectedError

    async def _get_doctype_id_by_name(self, doctype: str, **args: Any) -> int:
        if self._api_doctypes is not None:
            return await self._api_doctypes.get_id_by_name(doctype, **args)
        raise self.APINotConnectedError

    async def _make_permission_table(
        self, groups: list[str] | None = None
    ) -> PermissionTableType:
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
        tags: list[str],
        *,
        owner: str | None,
        groups: list[str] | None,
        make: bool = True,
        is_inbox_tag: bool = False,
        is_insensitive: bool = True,
        match: str = "",
        matching_algorithm: MatchingAlgorithmType = MatchingAlgorithmType.NONE,
        color: str = "#%06x" % random.randint(0, 2**24),
    ) -> list[int]:
        perms: PermissionTableType | None = await self._make_permission_table(
            groups
        )
        ret: list[int] = []
        for t in tags:
            try:
                ret.append(
                    await self._get_tag_id_by_name(
                        t,
                        make=make,
                        make_args={
                            "is_inbox_tag": is_inbox_tag,
                            "is_insensitive": is_insensitive,
                            "match": match,
                            "matching_algorithm": matching_algorithm,
                            "color": color,
                        },
                        permissions_table=perms,
                        owner=(
                            await self._get_user_id_by_name(owner)
                            if owner
                            else None
                        ),
                    )
                )

            except KeyError as err:
                raise self.MissingObjectError(
                    f"Tag '{t}' does not exist"
                    " (and upload.tags_must_exist is set)"
                ) from err

        return ret

    async def _get_or_make_correspondent(
        self,
        correspondent: str | None,
        *,
        owner: str | None = None,
        groups: list[str] | None = None,
        make: bool = True,
        is_insensitive: bool = True,
        match: str = "",
        matching_algorithm: MatchingAlgorithmType = MatchingAlgorithmType.AUTO,
        color: str = "#%06x" % random.randint(0, 2**24),
    ) -> int | None:
        if correspondent is None:
            return None

        perms: PermissionTableType | None = await self._make_permission_table(
            groups
        )
        try:
            return await self._get_correspondent_id_by_name(
                correspondent,
                make=make,
                make_args={
                    "match": match,
                    "is_insensitive": is_insensitive,
                    "matching_algorithm": matching_algorithm,
                    "color": color,
                },
                permissions_table=perms,
                owner=(
                    await self._get_user_id_by_name(owner) if owner else None
                ),
            )

        except KeyError as err:
            raise self.MissingObjectError(
                f"Correspondent '{correspondent}' does not exist "
                "(and upload.correspondent_must_exist is set)"
            ) from err

    async def upload(
        self,
        filenames: list[pathlib.Path],
        *,
        owner: str | None = None,
        groups: list[str] | None = None,
        correspondent: str | None = None,
        correspondent_must_exist: bool = False,
        tags: list[str] | None = None,
        tags_must_exist: bool = False,
        dateres: list[str] | None = None,
        nameres: list[str] | None = None,
        tries: int = 1,
    ) -> None:
        if not filenames:
            return

        if self._api is None:
            raise RuntimeError("API is not connected")

        try:
            if tags is not None:
                tag_ids: list[int] = await self._get_or_make_tags(
                    tags,
                    make=not tags_must_exist and not self._no_act,
                    owner=owner,
                    groups=groups,
                )
            else:
                tag_ids = []

        except self.MissingObjectError:
            if self._no_act and not tags_must_exist:
                logger.info(f"Would try to create tags: {tags}")
                tag_ids = []
            else:
                raise

        try:
            correspondent_id = await self._get_or_make_correspondent(
                correspondent,
                make=not correspondent_must_exist and not self._no_act,
                owner=owner,
                groups=groups,
            )

        except self.MissingObjectError:
            if self._no_act and not correspondent_must_exist:
                logger.info(
                    f"Would try to create correspondent: {correspondent}"
                )
                correspondent_id = None
            else:
                raise

        try:
            await asyncio.gather(
                *[
                    self._upload_single(
                        file,
                        owner=owner,
                        groups=groups,
                        tags=tag_ids,
                        correspondent=correspondent_id,
                        dateres=dateres,
                        nameres=nameres,
                    )
                    for file in filenames
                ]
            )

        except aiohttp.client_exceptions.ClientResponseError as err:
            logger.error(f"API request denied: {err}")

        return None

    def _make_title(self, filename: str, nameres: list[str] | None) -> str:
        for rgx in nameres or []:
            if rgx[0] == "s":
                delim: str = rgx[1]
                parts: list[str] = rgx.split(delim)
                if len(parts) not in (3, 4):
                    logger.error(f"Invalid regular expression: {rgx}")
                    continue

                res: str = re.sub(parts[1], parts[2], filename)
                logger.debug(f"namere: {filename} ~= {rgx} → {res}")
                filename = res

            else:
                logger.error(f"Regular expression must start with 's': {rgx}")
                continue

        return filename

    @staticmethod
    def _get_creation_date(
        filename: str, dateres: list[str]
    ) -> tuple[str | None, str]:
        for rgx in dateres:
            m: re.Match[str] | None = re.match(rgx, filename)
            if not m:
                continue

            matchdict: dict[str, Any] = m.groupdict()

            if ret := matchdict.get("date"):
                return ret, matchdict.get("remainder", filename)

        return None, filename

    async def _upload_single(
        self,
        file: pathlib.Path,
        *,
        owner: str | None,
        groups: list[str] | None,
        tags: list[int] | None,
        correspondent: int | None,
        dateres: list[str] | None = None,
        nameres: list[str] | None = None,
        tries: int = 1,
    ) -> int | str | tuple[int, int] | None:
        filename: str = str(file.stem)
        if dateres:
            creationdate, filename = self._get_creation_date(filename, dateres)
            if creationdate:
                logger.debug(
                    f"Extracted date {creationdate} from filename {file}"
                )
            else:
                logger.debug(f"Failed to extract date from filename {file}")
        else:
            creationdate = None

        title: str = self._make_title(filename or str(file.stem), nameres)

        logger.debug(f"Title extracted from {file}: {title}")

        async def _do_upload(
            **kwargs: Any,
        ) -> str | None:
            if self._no_act:
                logger.info(f"Would upload file {file}:")
                del kwargs["filename"]
                for k, v in kwargs.items():
                    if v is not None and v != []:
                        logger.info(f"  {k}: {v}")
                return None
            else:
                if self._api is not None:
                    async with async_open(file, "rb") as f:
                        draft = self._api.documents.draft(
                            document=await f.read(), **kwargs
                        )
                        taskid: str = await draft.save()
                    logger.info(f"File {file} uploaded, task ID {taskid}")
                    return taskid
                else:
                    raise self.APINotConnectedError

        try:
            return await _do_upload(
                filename=file.name,
                title=title,
                tags=tags,
                correspondent=correspondent,
                created=creationdate,
            )

        except aiohttp.client_exceptions.ServerTimeoutError as err:
            logger.warning(
                f"Connection problem during upload of file {file}: {err}"
            )

        except pypaperless.exceptions.BadJsonResponseError as err:
            logger.warning(
                "Paperless reported an error with "
                f"the upload of file {file}: {err}"
            )

        except FileNotFoundError as err:
            logger.error(f"File not found: {err.filename}")
            return None

        except Exception as err:
            logger.exception(
                f"Received other exception during upload of file {file}: {err}"
            )

        if (tries := tries - 1) > 0:
            logger.info(f"Upload of {file} failed, retrying {tries} time(s)…")
            await asyncio.sleep(1)
            return await self._upload_single(
                file,
                owner=owner,
                groups=groups,
                tags=tags,
                correspondent=correspondent,
                dateres=dateres,
                nameres=nameres,
                tries=tries,
            )

        else:
            logger.error(f"Upload of {file} failed all retries.")
            return None

    async def tags(self) -> Cache:
        if self._api_tags is not None:
            return await self._api_tags.get_all()

        raise self.APINotConnectedError
