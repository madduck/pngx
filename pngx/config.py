import tomllib
import platformdirs


class Config:

    def __init__(self, path=None):
        self._data = {}
        self._path = path

        self.load_file(path or self._get_config_file_path())

    @staticmethod
    def _get_config_file_path():
        cfgfile = platformdirs.user_config_path("pngx") / "config"
        return cfgfile if cfgfile.exists() else None

    def load_file(self, path):
        if path:
            with open(path, "rb") as f:
                self._data = tomllib.load(f)

    def get(self, key, default=None):
        rv = self._data
        try:
            keys = key.split(".")
            for k in keys[:-1]:
                rv = rv[k]

            return rv.get(keys[-1], default)

        except KeyError:
            raise KeyError(key)

    def set(self, key, value):
        d = self._data
        keys = key.split(".")
        for k in keys[:-1]:
            d = d.setdefault(k, {})

        d[keys[-1]] = value


def merge_cli_opts_into_cfg(
    opts, cfg, *, path=None, exclude=None, typemap=None
):
    exclude = () if exclude is None else exclude
    typemap = {} if typemap is None else typemap

    for opt, val in opts.items():
        if opt in exclude:
            continue

        elif val is not None:
            tgt = ".".join((path, opt)) if path else opt
            val = typemap.get(tgt, lambda s: s)(val)
            if cur := cfg.get(tgt):
                try:
                    cur.extend(val)
                except AttributeError:
                    pass
                else:
                    val = cur
            cfg.set(tgt, val)
