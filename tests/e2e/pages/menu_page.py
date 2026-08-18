"""The public menu — what a guest sees after scanning the QR code."""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from .base import BasePage, Locator


class MenuPage(BasePage):
    """Page object for `/<locale>/menu[/<category>[/<subcategory>]]`."""

    #: A product card. Only cards carry an `h3` inside the menu's lists, which
    #: keeps this independent of the utility classes on the grid.
    CARD: Locator = (By.CSS_SELECTOR, "main li:has(h3)")
    CARD_NAME: Locator = (By.CSS_SELECTOR, "h3")

    HEADING: Locator = (By.CSS_SELECTOR, "main h1")
    SECTION_HEADING: Locator = (By.CSS_SELECTOR, "main section h2")

    #: Live region announcing how many dishes are in view.
    RESULT_SUMMARY: Locator = (By.CSS_SELECTOR, "main p[aria-live='polite']")

    SEARCH_FIELD: Locator = (By.CSS_SELECTOR, "main input[type='search']")
    EMPTY_STATE: Locator = (By.CSS_SELECTOR, "main [data-empty-state], main h2 + p")

    #: Category filters are real links, so they are addressed by their href.
    CATEGORY_LINKS: Locator = (By.CSS_SELECTOR, "main nav ul a")
    ACTIVE_CATEGORY: Locator = (By.CSS_SELECTOR, "main nav ul a[aria-current='page']")

    #: The language control in the site header.
    LOCALE_LINKS: Locator = (By.CSS_SELECTOR, "header a[hreflang]")
    HEADER_NAV_LINKS: Locator = (By.CSS_SELECTOR, "header nav[aria-label] a:not([hreflang])")
    SITE_HEADER: Locator = (By.CSS_SELECTOR, "header")

    # ------------------------------------------------------------ navigation

    def open_menu(self, locale: str = "uz", *segments: str) -> None:
        """Open the menu for `locale`, optionally filtered by path segments."""
        suffix = "".join(f"/{segment}" for segment in segments)
        self.open(f"/{locale}/menu{suffix}")
        self.await_products()

    def await_products(self) -> None:
        """Block until at least one product card has rendered."""
        self.wait.until(
            lambda _: bool(self.find_all(self.CARD)), "no product card ever rendered"
        )

    # --------------------------------------------------------------- reading

    def product_names(self) -> list[str]:
        """Visible name of every card currently in the grid."""
        return [
            card.find_element(*self.CARD_NAME).text.strip()
            for card in self.find_all(self.CARD)
        ]

    def product_count(self) -> int:
        """How many cards are in the grid right now."""
        return len(self.find_all(self.CARD))

    def heading(self) -> str:
        """The `h1`: the site title, or the selected section's name."""
        return self.text_of(self.HEADING)

    def result_summary(self) -> str:
        """Text of the live region under the search box."""
        return self.text_of(self.RESULT_SUMMARY)

    def category_paths(self) -> list[str]:
        """Root-relative href of every category filter, in render order."""
        return [
            link.get_attribute("href").removeprefix(self.base_url)
            for link in self.find_all(self.CATEGORY_LINKS)
        ]

    def active_category_path(self) -> str:
        """Href of the filter marked `aria-current="page"`."""
        return self.find(self.ACTIVE_CATEGORY).get_attribute("href").removeprefix(self.base_url)

    def header_nav_labels(self) -> list[str]:
        """Labels of the site navigation, which come from the message catalog."""
        return [label for label in self.texts_of(self.HEADER_NAV_LINKS) if label]

    # ---------------------------------------------------------- interactions

    def _category_link(self, path: str) -> WebElement:
        for link in self.find_all(self.CATEGORY_LINKS):
            if link.get_attribute("href").removeprefix(self.base_url) == path:
                return link
        raise AssertionError(f"no category filter links to {path}; have {self.category_paths()}")

    def click_category(self, path: str) -> None:
        """Click the filter whose href is `path` and wait for the new route."""
        link = self._category_link(path)
        self.scroll_into_middle(link)
        link.click()
        self.wait_for_path(path)
        self.await_products()

    def search(self, term: str) -> None:
        """Type into the search box and wait for the grid to settle.

        The field debounces by 200ms, so the wait is on the live region's text
        changing rather than on a fixed pause.
        """
        before = self.result_summary()
        self.type_into(self.SEARCH_FIELD, term)
        self.wait.until(
            lambda _: self.result_summary() != before,
            f"the result summary never changed after searching for {term!r}",
        )

    def switch_language(self, locale: str) -> None:
        """Follow the header's link to the same route in another language."""
        for link in self.find_all(self.LOCALE_LINKS):
            if link.get_attribute("hreflang") == locale:
                self.scroll_into_middle(link)
                link.click()
                self.wait.until(
                    lambda driver: f"/{locale}/" in driver.current_url,
                    f"never navigated to the {locale} route",
                )
                self.await_products()
                return
        raise AssertionError(f"no language link for {locale!r}")
