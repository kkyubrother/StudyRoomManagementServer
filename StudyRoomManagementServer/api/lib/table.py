from typing import Tuple

from flask import (
    request,
)


def get_limit_offset() -> Tuple[int, int]:
    """GET 에서 limit 과 offset 을 가져온다."""
    limit, offset = 10, 1

    limit = request.args.get("length", limit, type=int)
    limit = request.args.get("per_page", limit, type=int)

    offset = int(request.args.get("start", offset, type=int) / limit) + 1
    offset = request.args.get("page", offset, type=int)

    return limit, offset,
