"""API client the fixtures use to create and clean up their own data.

Tests never touch the database directly. Every row a test needs is created
through the same REST API the admin panel calls, and removed again in teardown,
which is what makes the suite repeatable and order-independent.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import requests

from .config import Settings

#: How long a single API call may take before it is treated as a failure.
TIMEOUT_SECONDS = 30

#: Largest `page_size` the API accepts, per the pagination contract.
MAX_PAGE_SIZE = 100

#: Cookies the front end writes for an authenticated panel session.
ACCESS_COOKIE = "bk_access"
REFRESH_COOKIE = "bk_refresh"


class ApiError(RuntimeError):
    """An API call returned a status the suite cannot continue from."""

    def __init__(self, method: str, url: str, response: requests.Response) -> None:
        super().__init__(f"{method} {url} -> {response.status_code}: {response.text[:400]}")
        self.status_code = response.status_code


@dataclass
class Product:
    """A product created for one test."""

    id: int
    slug: str
    names: dict[str, str]
    """Translated name per language code."""

    price: int


@dataclass
class Category:
    """A category created for one test run."""

    id: int
    slug: str
    names: dict[str, str]


@dataclass
class Table:
    """A table created for one test, with the token printed in its QR code."""

    id: int
    number: int
    token: str


@dataclass
class AdminApi:
    """Authenticated client for the `admin` half of the API."""

    settings: Settings
    session: requests.Session = field(default_factory=requests.Session)
    access_token: str = ""

    def sign_in(self) -> None:
        """Exchange the configured credentials for an access token."""
        response = self.session.post(
            self.settings.api("/auth/token/"),
            json={
                "username": self.settings.admin_username,
                "password": self.settings.admin_password,
            },
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise ApiError("POST", "/auth/token/", response)

        self.access_token = response.json()["access"]
        self.session.headers["Authorization"] = f"Bearer {self.access_token}"

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = self.settings.api(path)
        response = self.session.request(method, url, timeout=TIMEOUT_SECONDS, **kwargs)
        if response.status_code >= 400:
            raise ApiError(method, path, response)
        return response

    # ------------------------------------------------------------- categories

    def create_category(
        self,
        *,
        names: dict[str, str],
        parent: int | None = None,
        slug: str | None = None,
        order: int = 0,
    ) -> Category:
        """Create a category with one translation per entry in `names`."""
        payload: dict[str, Any] = {
            "slug": slug or f"e2e-{uuid.uuid4().hex[:10]}",
            "order": order,
            "is_active": True,
            "translations": [
                {"language": language, "name": name} for language, name in names.items()
            ],
        }
        if parent is not None:
            payload["parent"] = parent

        body = self._request("POST", "/admin/categories/", json=payload).json()
        return Category(id=body["id"], slug=body["slug"], names=dict(names))

    def delete_category(self, category_id: int) -> None:
        """Remove a category. Its products must be gone first (the API 409s)."""
        self._request("DELETE", f"/admin/categories/{category_id}/")

    # --------------------------------------------------------------- products

    def create_product(
        self,
        *,
        category_id: int,
        names: dict[str, str],
        price: int = 25000,
        descriptions: dict[str, str] | None = None,
        is_available: bool = True,
        order: int = 0,
    ) -> Product:
        """Create a product. `names` must include the required `uz` entry."""
        descriptions = descriptions or {}
        payload = {
            "category": category_id,
            "price": price,
            "is_available": is_available,
            "order": order,
            "translations": [
                {
                    "language": language,
                    "name": name,
                    "description": descriptions.get(language, ""),
                }
                for language, name in names.items()
            ],
        }

        body = self._request("POST", "/admin/products/", json=payload).json()
        return Product(id=body["id"], slug=body["slug"], names=dict(names), price=price)

    def get_product(self, product_id: int) -> dict[str, Any] | None:
        """Return a product, or `None` when it no longer exists."""
        try:
            return self._request("GET", f"/admin/products/{product_id}/").json()
        except ApiError as error:
            if error.status_code == 404:
                return None
            raise

    def list_products(self, *, category_slug: str | None = None) -> list[dict[str, Any]]:
        """Every admin product, optionally only those in one category.

        The admin list endpoint has no `search` parameter — it filters by
        category and nothing else, and an unknown parameter is ignored rather
        than rejected — so callers that need to find something walk the pages.
        `category` matches on the category's **slug**, not its id.
        """
        params: dict[str, Any] = {"page_size": MAX_PAGE_SIZE}
        if category_slug is not None:
            params["category"] = category_slug

        items: list[dict[str, Any]] = []
        path: str | None = "/admin/products/"
        while path is not None:
            body = self._request("GET", path, params=params).json()
            items.extend(body["results"])
            # `next` is absolute and already carries the query string.
            next_url = body.get("next")
            path = next_url.removeprefix(self.settings.api_url) if next_url else None
            params = {}
        return items

    def find_product_by_name(
        self, name: str, *, category_slug: str | None = None
    ) -> dict[str, Any] | None:
        """Look a product up by an exact translated name."""
        for item in self.list_products(category_slug=category_slug):
            if any(row["name"] == name for row in item["translations"]):
                return item
        return None

    def delete_product(self, product_id: int) -> None:
        """Remove a product, tolerating one that a test already deleted."""
        try:
            self._request("DELETE", f"/admin/products/{product_id}/")
        except ApiError as error:
            if error.status_code != 404:
                raise

    # ----------------------------------------------------------------- tables

    def create_table(self, *, number: int, label: str = "") -> Table:
        """Create a table and return the token its QR code encodes."""
        body = self._request(
            "POST",
            "/admin/tables/",
            json={"number": number, "label": label, "is_active": True},
        ).json()
        return Table(id=body["id"], number=body["number"], token=body["token"])

    def delete_table(self, table_id: int) -> None:
        """Remove a table, tolerating one that a test already deleted."""
        try:
            self._request("DELETE", f"/admin/tables/{table_id}/")
        except ApiError as error:
            if error.status_code != 404:
                raise


def open_panel_session(settings: Settings) -> dict[str, str]:
    """Sign in through the front end and return its two session cookies.

    The panel's tokens live in httpOnly cookies written by the Next.js route
    handler, never in the document. Obtaining them once per session and
    injecting them into each browser keeps every admin test to a single
    credential exchange, which matters because the API throttles logins to
    5/min per IP.
    """
    response = requests.post(
        f"{settings.web_url}/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
        timeout=TIMEOUT_SECONDS,
    )
    if response.status_code != 200:
        raise RuntimeError(
            f"Front-end login failed with {response.status_code}: {response.text[:400]}"
        )

    cookies = response.cookies
    missing = [name for name in (ACCESS_COOKIE, REFRESH_COOKIE) if name not in cookies]
    if missing:
        raise RuntimeError(f"Login response did not set {', '.join(missing)}")

    return {ACCESS_COOKIE: cookies[ACCESS_COOKIE], REFRESH_COOKIE: cookies[REFRESH_COOKIE]}
