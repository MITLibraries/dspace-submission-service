import logging
from collections.abc import Generator
from contextlib import contextmanager
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import requests

logger = logging.getLogger(__name__)

MAX_BODY_BYTES = 10 * 1024
TRUNCATION_SUFFIX = "...[truncated]"

EXCLUDED_URL_FRAGMENTS = ("/authn/",)

FAILURE_STATUS_THRESHOLD = 400
REDACTED = "<redacted>"
SENSITIVE_REQUEST_HEADERS = frozenset({"authorization", "cookie", "x-xsrf-token"})
LOGGED_RESPONSE_HEADERS = ("Content-Type", "Retry-After")


class DSpaceResponseLabel(StrEnum):
    """Keys for Submission.dspace_responses based on the DSS method."""

    CREATE_ITEM = "create_item"
    CREATE_BUNDLE = "create_bundle"
    CREATE_BITSTREAM = "create_bitstream"
    UPLOAD_NEW_ITEM_BITSTREAMS = "upload_new_item_bitstreams"
    ADD_METADATA = "add_metadata"
    DELETE_BITSTREAM = "delete_bitstream"
    DELETE_ITEM = "delete_item"


@contextmanager
def capture_responses(
    session: "requests.Session",
    collector: dict[str, list[dict]],
    label: DSpaceResponseLabel,
) -> Generator[None]:
    """Record DSpace responses into a dict.

    The hook is attached only while the wrapped call runs, so requests made outside
    this context are never recorded.

    Args:
        session: The requests session to attach the response hook to.
        collector: A dict to collect parsed responses.
        label: The label under which to store the captured responses.
    """

    def hook(
        response: "requests.Response",
        **_kwargs: Any,  # noqa: ANN401
    ) -> None:
        try:
            if any(f in response.url for f in EXCLUDED_URL_FRAGMENTS):
                return
            entry = parse_response(response)
            collector.setdefault(label, []).append(entry)
            logger.debug(
                "DSpace response captured [%s]: %s %s -> %s",
                label,
                entry["method"],
                entry["url"],
                entry["status_code"],
            )
        except Exception:
            logger.warning("Failed to capture DSpace response", exc_info=True)

    session.hooks["response"].append(hook)
    try:
        yield
    finally:
        session.hooks["response"].remove(hook)


@contextmanager
def log_failed_responses(session: "requests.Session", context: str) -> Generator[None]:
    """Log every failed (status >= 400) DSpace response made through a session.

    Authentication requests (EXCLUDED_URL_FRAGMENTS) are never logged, so login
    credentials cannot reach the logs.

    The hook is attached only while the wrapped block runs, so a cached, shared
    session never keeps a hook carrying a stale submission's context.

    Args:
        session: The requests session to attach the response hook to.
        context: Text identifying the submission, included in each log record.
    """

    def hook(
        response: "requests.Response",
        **_kwargs: Any,  # noqa: ANN401
    ) -> None:
        try:
            if response.status_code < FAILURE_STATUS_THRESHOLD or any(
                f in response.url for f in EXCLUDED_URL_FRAGMENTS
            ):
                return
            logger.error(
                "DSpace request failed [%s]: %s",
                context,
                format_failed_exchange(response),
            )
        except Exception:
            logger.warning("Failed to log DSpace response", exc_info=True)

    session.hooks["response"].append(hook)
    try:
        yield
    finally:
        session.hooks["response"].remove(hook)


def format_failed_exchange(response: "requests.Response") -> str:
    """Render a failed request/response pair for logging."""
    headers = {
        name: response.headers[name]
        for name in LOGGED_RESPONSE_HEADERS
        if name in response.headers
    }
    elapsed = response.elapsed.total_seconds() if response.elapsed is not None else None
    return (
        f"request=({format_request(response.request)}) "
        f"response=(status={response.status_code} reason={response.reason!r} "
        f"elapsed={elapsed} headers={headers} body={parse_response(response)['body']!r})"
    )


def format_request(request: "requests.PreparedRequest | None") -> str:
    """Render a request for logging, redacting credentials."""
    if request is None:
        return "<no request>"
    headers = {
        name: REDACTED if name.lower() in SENSITIVE_REQUEST_HEADERS else value
        for name, value in request.headers.items()
    }
    raw = request.body
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    body = truncate_body(raw or "")
    return f"{request.method} {request.url} headers={headers} body={body!r}"


def truncate_body(text: str) -> str:
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= MAX_BODY_BYTES:
        return text
    return encoded[:MAX_BODY_BYTES].decode("utf-8", errors="ignore") + TRUNCATION_SUFFIX


def parse_response(response: "requests.Response") -> dict[str, Any]:
    try:
        body = truncate_body(response.text)
    except Exception:
        logger.warning("Failed to read DSpace response body", exc_info=True)
        body = "<unreadable>"
    return {
        "status_code": response.status_code,
        "url": response.url,
        "method": response.request.method if response.request else None,
        "elapsed": (
            response.elapsed.total_seconds() if response.elapsed is not None else None
        ),
        "body": body,
    }
