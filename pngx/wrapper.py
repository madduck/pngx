class PaperlessObjectWrapper:

    def __init__(self, obj, *, namecol="name"):
        self._obj = obj
        self._cache = None
        self._namecol = namecol

    async def _load_cache(self, *, reload=False):
        if not self._cache or reload:
            self._cache = {
                getattr(o, self._namecol): o.id async for o in self._obj
            }

    async def get_id_by_name(
        self,
        name,
        *,
        make=False,
        make_args=None,
        owner=None,
        permissions_table=None,
        draft_cb=None,
    ):
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

    async def get_all(self):
        await self._load_cache()
        return self._cache.copy()

