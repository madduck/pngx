# needed < 3.14 so that annotations aren't evaluated
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from typing import Any

    from pypaperless.models.common import PermissionTableType

    type Cache = dict[str, int]


class PaperlessObjectWrapper:
    def __init__(self, obj: Any, *, namecol: str = "name") -> None:
        self._obj = obj
        self._namecol = namecol
        self._cache: Cache = {}

    async def _load_cache(self, *, reload: bool = False) -> None:
        if not self._cache or reload:
            self._cache = {
                getattr(o, self._namecol): o.id async for o in self._obj
            }

    async def get_id_by_name(
        self,
        name: str,
        *,
        make: bool = False,
        make_args: Mapping[str, Any] | None = None,
        owner: str | None = None,
        permissions_table: PermissionTableType | None = None,
        draft_cb: Callable[..., None] | None = None,
    ) -> int:
        try:
            await self._load_cache()
            ret = self._cache[name]

        except KeyError:
            if make:
                make_args = make_args or {}
                draft = self._obj.draft(name=name, **make_args)
                if owner:
                    draft.owner = owner
                if permissions_table:
                    draft.set_permissions = permissions_table
                if callable(draft_cb):
                    draft_cb(draft)
                ret = await draft.save()
                self._cache[name] = ret

            else:
                raise

        return ret

    async def get_all(self, reload: bool = False) -> Cache:
        await self._load_cache(reload=reload)
        return self._cache.copy()
