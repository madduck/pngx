import asyncio
import functools
from collections.abc import Callable, Coroutine
from typing import Any, Never, cast


def asyncio_run[T, **P](fn: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
        asyncio.run(cast(Coroutine[Any, Any, Never], fn(*args, **kwargs)))

    return wrapper
