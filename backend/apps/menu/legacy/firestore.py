"""Minimal reader for the Firestore REST API.

The legacy collection is world readable, so the migration needs no service account
and no `google-cloud-firestore` dependency — one paginated GET and a decoder for
Firestore's typed-value JSON is the whole surface.

Only the value types the legacy documents actually use are decoded; anything else
raises rather than being silently dropped, so a schema surprise fails loudly.
"""

import json
import time
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://firestore.googleapis.com/v1"
DEFAULT_PAGE_SIZE = 50
DEFAULT_TIMEOUT = 30
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5


class FirestoreError(RuntimeError):
    """The upstream collection could not be read or understood."""


@dataclass(frozen=True, slots=True)
class LegacyDocument:
    """One decoded `menu_items` document."""

    id: str
    fields: dict[str, Any]

    def text_map(self, key: str) -> dict[str, str]:
        """A `{language: text}` field, tolerating an absent or non-map value."""
        value = self.fields.get(key)
        if not isinstance(value, Mapping):
            return {}
        return {k: v for k, v in value.items() if isinstance(v, str)}

    def string(self, key: str) -> str | None:
        value = self.fields.get(key)
        return value if isinstance(value, str) else None

    def integer(self, key: str) -> int | None:
        value = self.fields.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) else None


def decode_value(value: Mapping[str, Any]) -> Any:
    """Turn one Firestore typed value into a plain Python value."""
    if not isinstance(value, Mapping) or len(value) != 1:
        raise FirestoreError(f"Not a Firestore typed value: {value!r}")

    kind, payload = next(iter(value.items()))
    match kind:
        case "stringValue" | "timestampValue":
            return payload
        case "integerValue":
            return int(payload)
        case "doubleValue":
            return float(payload)
        case "booleanValue":
            return bool(payload)
        case "nullValue":
            return None
        case "mapValue":
            return decode_fields(payload.get("fields", {}))
        case "arrayValue":
            return [decode_value(item) for item in payload.get("values", [])]
    raise FirestoreError(f"Unsupported Firestore value type: {kind}")


def decode_fields(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {name: decode_value(value) for name, value in fields.items()}


def decode_document(document: Mapping[str, Any]) -> LegacyDocument:
    """Decode one API document, taking the id from its resource path."""
    name = document.get("name")
    if not isinstance(name, str) or "/" not in name:
        raise FirestoreError(f"Document has no usable resource name: {document.get('name')!r}")
    return LegacyDocument(
        id=name.rsplit("/", 1)[1], fields=decode_fields(document.get("fields", {}))
    )


class FirestoreCollection:
    """Paginated reader over one public Firestore collection."""

    def __init__(
        self,
        project: str,
        collection: str,
        *,
        page_size: int = DEFAULT_PAGE_SIZE,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self.project = project
        self.collection = collection
        self.page_size = page_size
        self.timeout = timeout
        self.session = session or requests.Session()

    @property
    def url(self) -> str:
        return f"{BASE_URL}/projects/{self.project}/databases/(default)/documents/{self.collection}"

    def __iter__(self) -> Iterator[LegacyDocument]:
        """Yield every document, following `nextPageToken` to the end."""
        token: str | None = None
        seen_tokens: set[str] = set()

        while True:
            page = self._get_page(token)
            for document in page.get("documents", []):
                yield decode_document(document)

            token = page.get("nextPageToken")
            if not token:
                return
            if token in seen_tokens:
                # Firestore hands back the same token when a page is empty but not
                # final; looping on it would spin forever.
                raise FirestoreError("Pagination stalled: nextPageToken repeated.")
            seen_tokens.add(token)

    def _get_page(self, token: str | None) -> dict[str, Any]:
        params: dict[str, Any] = {"pageSize": self.page_size}
        if token:
            params["pageToken"] = token

        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self.session.get(self.url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < MAX_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)

        raise FirestoreError(f"Could not read {self.url}: {last_error}") from last_error


def load_documents(path: Path) -> list[LegacyDocument]:
    """Decode documents from a saved API response.

    Accepts a single response object, a bare list of documents, or a list of page
    objects, so a snapshot taken any of the obvious ways can be replayed offline.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))

    if isinstance(payload, Mapping):
        pages: list[Any] = [payload]
    elif isinstance(payload, list):
        pages = payload
    else:
        raise FirestoreError(f"Unreadable snapshot at {path}")

    documents: list[LegacyDocument] = []
    for page in pages:
        if isinstance(page, Mapping) and "documents" in page:
            documents.extend(decode_document(item) for item in page["documents"])
        elif isinstance(page, Mapping) and "name" in page:
            documents.append(decode_document(page))
        else:
            raise FirestoreError(f"Unreadable snapshot entry in {path}: {page!r}")
    return documents
