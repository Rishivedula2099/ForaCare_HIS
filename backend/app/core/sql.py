"""P9-B01: SQL helpers."""

LIKE_ESCAPE = "\\"


def like_contains(term: str) -> str:
    """`%term%` with LIKE metacharacters escaped, so a user-typed `%` or `_`
    matches literally. Pair with `.ilike(pattern, escape=LIKE_ESCAPE)`."""
    escaped = (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", LIKE_ESCAPE + "%")
        .replace("_", LIKE_ESCAPE + "_")
    )
    return f"%{escaped}%"


def like_prefix(prefix: str) -> str:
    """`prefix%` with LIKE metacharacters in the prefix escaped."""
    return like_contains(prefix)[1:-1] + "%"
