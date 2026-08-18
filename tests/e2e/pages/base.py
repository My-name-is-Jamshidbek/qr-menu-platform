"""Shared behaviour for every page object."""

from __future__ import annotations

from typing import Any

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.ui import WebDriverWait

#: A CSS locator: `(By.CSS_SELECTOR, "…")`.
Locator = tuple[str, str]

#: React attaches `__reactFiber$…` / `__reactProps$…` to the DOM nodes it owns
#: as it hydrates. Their presence is the signal that a server-rendered control
#: is now wired to its event handlers — without it, typing into a controlled
#: input writes a value React promptly discards.
IS_HYDRATED = "return Object.keys(arguments[0]).some((key) => key.startsWith('__react'));"

#: What is actually painted at a point, and how it relates to a given element.
HIT_TARGET = """
const element = arguments[0];
const box = element.getBoundingClientRect();
const point = document.elementFromPoint(
  box.left + box.width / 2,
  box.top + box.height / 2
);
if (!point) {
  return {resolved: false, isSelf: false, isDescendant: false, description: 'nothing'};
}
return {
  resolved: true,
  isSelf: point === element,
  isDescendant: element.contains(point),
  description:
    point.tagName.toLowerCase() +
    (point.id ? '#' + point.id : '') +
    (typeof point.className === 'string' && point.className
      ? '.' + point.className.trim().split(/\\s+/).slice(0, 3).join('.')
      : '')
};
"""


class BasePage:
    """Locating, waiting and clicking, with no `time.sleep` anywhere."""

    def __init__(self, driver: WebDriver, base_url: str, timeout: int) -> None:
        self.driver = driver
        self.base_url = base_url
        self.timeout = timeout
        self.wait = WebDriverWait(driver, timeout)

    # ------------------------------------------------------------ navigation

    def open(self, path: str) -> None:
        """Load a root-relative path on the front end."""
        self.driver.get(f"{self.base_url}{path}")

    @property
    def path(self) -> str:
        """Current URL with the origin stripped, e.g. `/uz/menu/desserts`."""
        return self.driver.current_url.removeprefix(self.base_url)

    def wait_for_path(self, path: str) -> None:
        """Block until the browser is on exactly `path`."""
        self.wait.until(
            lambda _: self.path == path,
            f"expected to be on {path}, still on {self.path}",
        )

    # -------------------------------------------------------------- locating

    def find(self, locator: Locator) -> WebElement:
        """First matching element, once it is in the DOM."""
        return self.wait.until(expected.presence_of_element_located(locator))

    def find_all(self, locator: Locator) -> list[WebElement]:
        """Every current match. Empty when nothing matches — never waits."""
        return self.driver.find_elements(*locator)

    def visible(self, locator: Locator) -> WebElement:
        """First matching element, once it is displayed."""
        return self.wait.until(expected.visibility_of_element_located(locator))

    def is_present(self, locator: Locator) -> bool:
        """Whether anything matches right now."""
        return bool(self.find_all(locator))

    def text_of(self, locator: Locator) -> str:
        """Trimmed visible text of the first match."""
        return self.find(locator).text.strip()

    def texts_of(self, locator: Locator) -> list[str]:
        """Trimmed visible text of every match."""
        return [element.text.strip() for element in self.find_all(locator)]

    # ---------------------------------------------------------- interactions

    def await_hydration(self, locator: Locator) -> WebElement:
        """Block until React owns the element, then return it."""
        element = self.find(locator)
        self.wait.until(
            lambda driver: driver.execute_script(IS_HYDRATED, element),
            f"{locator[1]} never hydrated",
        )
        return element

    def scroll_into_middle(self, element: WebElement) -> None:
        """Centre an element vertically.

        WebDriver's own scroll parks an element flush against the top of the
        viewport, where the 64px sticky header covers it — an artefact of the
        harness, not something a guest scrolling by hand would hit.
        """
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element
        )

    def click(self, locator: Locator) -> None:
        """Scroll an element into clear view and click it."""
        element = self.find(locator)
        self.scroll_into_middle(element)
        self.wait.until(expected.element_to_be_clickable(locator)).click()

    def type_into(self, locator: Locator, text: str) -> None:
        """Type into a hydrated field, replacing whatever it holds.

        Select-all then delete, rather than `WebElement.clear()`: on a React
        controlled input `clear()` rewrites the DOM value without producing the
        events React listens for, so the component's state keeps the old value
        and the next render puts it straight back.
        """
        field = self.await_hydration(locator)
        self.scroll_into_middle(field)
        field.send_keys(Keys.CONTROL, "a")
        field.send_keys(Keys.DELETE)
        if text:
            field.send_keys(text)

    def hit_target(self, locator: Locator) -> dict[str, Any]:
        """What `document.elementFromPoint` returns at the element's centre.

        The answer distinguishes "the button is on top", "something inside the
        button is on top" and "an unrelated element covers it" — the last being
        the failure mode that made the original app's primary action inert.
        """
        element = self.find(locator)
        self.scroll_into_middle(element)
        result: dict[str, Any] = self.driver.execute_script(HIT_TARGET, element)
        return result

    # ------------------------------------------------------------ page shape

    def viewport(self) -> dict[str, int]:
        """Layout viewport and full scrollable size of the document."""
        return self.driver.execute_script(
            """
            const root = document.documentElement;
            return {
              width: root.clientWidth,
              height: root.clientHeight,
              scrollWidth: Math.max(root.scrollWidth, document.body.scrollWidth),
              scrollHeight: Math.max(root.scrollHeight, document.body.scrollHeight)
            };
            """
        )

    def elements_overflowing_horizontally(self) -> list[dict[str, Any]]:
        """Every element painted outside the horizontal bounds of the viewport.

        Reported alongside a failed overflow assertion so the message names the
        element at fault instead of only the pixel count.
        """
        return self.driver.execute_script(
            """
            const width = document.documentElement.clientWidth;
            const offenders = [];
            for (const element of document.querySelectorAll('body *')) {
              const box = element.getBoundingClientRect();
              if (box.width === 0 || box.height === 0) continue;
              if (box.right > width + 1 || box.left < -1) {
                offenders.push({
                  tag: element.tagName.toLowerCase(),
                  classes: (element.className || '').toString().slice(0, 60),
                  left: Math.round(box.left),
                  right: Math.round(box.right)
                });
              }
            }
            return offenders;
            """
        )

    @staticmethod
    def css(selector: str) -> Locator:
        """Shorthand for a CSS locator."""
        return (By.CSS_SELECTOR, selector)
