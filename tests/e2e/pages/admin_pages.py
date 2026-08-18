"""Page objects for the staff panel."""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from .base import BasePage, Locator


class AdminLoginPage(BasePage):
    """Page object for `/<locale>/admin/login`."""

    USERNAME: Locator = (By.CSS_SELECTOR, "form input[name='username']")
    PASSWORD: Locator = (By.CSS_SELECTOR, "form input[name='password']")
    SUBMIT: Locator = (By.CSS_SELECTOR, "[data-testid='admin-login-submit']")
    ALERT: Locator = (By.CSS_SELECTOR, "form [role='alert']")

    def open_login(self, locale: str = "uz", next_path: str | None = None) -> None:
        """Open the sign-in screen, optionally with a return path."""
        query = f"?next={next_path}" if next_path else ""
        self.open(f"/{locale}/admin/login{query}")
        self.await_hydration(self.SUBMIT)

    def sign_in(self, username: str, password: str) -> None:
        """Fill the form and submit it. Does not assume the attempt succeeds."""
        self.await_hydration(self.SUBMIT)
        self.type_into(self.USERNAME, username)
        self.type_into(self.PASSWORD, password)
        self.click(self.SUBMIT)

    def error_message(self) -> str:
        """Text of the alert region, once the form has reported a failure."""
        self.wait.until(
            lambda _: self.text_of(self.ALERT) != "",
            "the login form never reported an error",
        )
        return self.text_of(self.ALERT)

    def has_error(self) -> bool:
        """Whether the alert region currently holds a message."""
        return self.is_present(self.ALERT) and self.text_of(self.ALERT) != ""


class AdminProductsPage(BasePage):
    """Page object for the product list at `/<locale>/admin/products`."""

    CREATE_BUTTON: Locator = (By.CSS_SELECTOR, "[data-testid='admin-create-product']")
    ROWS: Locator = (By.CSS_SELECTOR, "table tbody tr")
    ROW_NAME: Locator = (By.CSS_SELECTOR, "th[scope='row'] a")
    HEADING: Locator = (By.CSS_SELECTOR, "h1")
    SEARCH_FIELD: Locator = (By.CSS_SELECTOR, "form[role='search'] input[type='search']")
    SEARCH_SUBMIT: Locator = (By.CSS_SELECTOR, "form[role='search'] button[type='submit']")
    SUCCESS_TOAST: Locator = (By.CSS_SELECTOR, "section > div[class*='border']")

    def open_products(self, locale: str = "uz") -> None:
        """Open the product list and wait for its primary action."""
        self.open(f"/{locale}/admin/products")
        self.find(self.CREATE_BUTTON)

    def row_names(self) -> list[str]:
        """Product name shown in each row of the current page of results."""
        return [row.find_element(*self.ROW_NAME).text.strip() for row in self.find_all(self.ROWS)]

    def search_for(self, term: str) -> None:
        """Use the server-side toolbar filter, which reloads the page.

        `q` is the query parameter the panel reads (`LIST_PARAMS.search`).
        """
        self.type_into(self.SEARCH_FIELD, term)
        self.click(self.SEARCH_SUBMIT)
        self.wait.until(
            lambda driver: "q=" in driver.current_url,
            "the search form never reached the query string",
        )
        self.find(self.CREATE_BUTTON)

    def start_create(self) -> None:
        """Follow the "add product" action to the creation form."""
        self.click(self.CREATE_BUTTON)
        self.wait.until(
            lambda driver: driver.current_url.endswith("/products/new"),
            "the add-product action did not open the creation form",
        )

    def open_product(self, name: str) -> None:
        """Open the edit screen of the row whose name is exactly `name`."""
        for row in self.find_all(self.ROWS):
            link = row.find_element(*self.ROW_NAME)
            if link.text.strip() == name:
                self.scroll_into_middle(link)
                link.click()
                self.wait.until(
                    lambda driver: "/products/" in driver.current_url
                    and not driver.current_url.endswith("/products"),
                    "the row link did not open a product",
                )
                return
        raise AssertionError(f"no row named {name!r}; have {self.row_names()}")


class ProductFormPage(BasePage):
    """Page object for the shared create/edit product form."""

    FORM: Locator = (By.CSS_SELECTOR, "[data-testid='admin-product-form']")
    CATEGORY: Locator = (By.CSS_SELECTOR, "select[name='category']")
    PRICE: Locator = (By.CSS_SELECTOR, "input[name='price']")
    SAVE: Locator = (By.CSS_SELECTOR, "[data-testid='admin-save-product']")
    STATUS: Locator = (By.CSS_SELECTOR, "form [role='status']")
    HEADING: Locator = (By.CSS_SELECTOR, "h1")

    DELETE: Locator = (By.CSS_SELECTOR, "[data-testid='admin-delete-product']")
    CONFIRM_DELETE: Locator = (By.CSS_SELECTOR, "[data-testid='admin-confirm-delete']")
    DIALOG: Locator = (By.CSS_SELECTOR, "dialog[open]")

    @staticmethod
    def name_field(language: str) -> Locator:
        """Locator for the translated name of `language`."""
        return (By.CSS_SELECTOR, f"input[name='name_{language}']")

    def await_form(self) -> None:
        """Block until the form is present and hydrated."""
        self.await_hydration(self.FORM)

    def choose_category(self, label_fragment: str) -> None:
        """Pick the first category whose option label contains `label_fragment`."""
        select = Select(self.find(self.CATEGORY))
        for option in select.options:
            if label_fragment in option.text:
                select.select_by_value(option.get_attribute("value"))
                return
        raise AssertionError(
            f"no category option contains {label_fragment!r}; "
            f"have {[option.text for option in select.options]}"
        )

    def set_price(self, price: int) -> None:
        """Replace the price with `price`, in whole so'm."""
        self.type_into(self.PRICE, str(price))

    def set_name(self, language: str, name: str) -> None:
        """Replace the translated name for `language`."""
        self.type_into(self.name_field(language), name)

    def name_value(self, language: str) -> str:
        """Current value of a translated name field."""
        return self.find(self.name_field(language)).get_attribute("value")

    def price_value(self) -> str:
        """Current value of the price field."""
        return self.find(self.PRICE).get_attribute("value")

    def heading(self) -> str:
        """The `h1`, which shows the product's translated name when editing."""
        return self.text_of(self.HEADING)

    def save(self) -> None:
        """Submit the form. The caller decides what outcome to wait for."""
        self.click(self.SAVE)

    def save_and_await_status(self) -> str:
        """Submit and return the message the form reports."""
        self.save()
        self.wait.until(
            lambda _: self.text_of(self.STATUS) != "",
            "the form never reported a save result",
        )
        return self.text_of(self.STATUS)

    def delete(self) -> None:
        """Open the confirmation dialog and confirm the deletion."""
        self.click(self.DELETE)
        self.visible(self.DIALOG)
        self.click(self.CONFIRM_DELETE)

    def confirm_dialog(self) -> WebElement:
        """The open confirmation dialog."""
        return self.visible(self.DIALOG)
