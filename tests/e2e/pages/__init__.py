"""Page objects for the BOSS KAFE end-to-end suite.

Every selector lives here and nowhere else, so a markup change is one edit.
"""

from .admin_pages import AdminLoginPage, AdminProductsPage, ProductFormPage
from .base import BasePage, Locator
from .menu_page import MenuPage

__all__ = [
    "AdminLoginPage",
    "AdminProductsPage",
    "BasePage",
    "Locator",
    "MenuPage",
    "ProductFormPage",
]
