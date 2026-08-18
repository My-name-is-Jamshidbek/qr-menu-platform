"""Menu routes: the public storefront reads and the staff CRUD surface."""

from django.urls import path

from apps.menu import signals  # noqa: F401  (importing connects the cache receivers)
from apps.menu.api.admin import (
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminProductDetailView,
    AdminProductImageCreateView,
    AdminProductImageDestroyView,
    AdminProductListCreateView,
    AdminStatsView,
)
from apps.menu.api.public import MenuView, ProductDetailView, ProductListView

app_name = "menu"

public_urlpatterns = [
    path("menu/", MenuView.as_view(), name="menu"),
    path("products/", ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", ProductDetailView.as_view(), name="product-detail"),
]

admin_urlpatterns = [
    path("admin/products/", AdminProductListCreateView.as_view(), name="admin-product-list"),
    path(
        "admin/products/<int:pk>/",
        AdminProductDetailView.as_view(),
        name="admin-product-detail",
    ),
    path(
        "admin/products/<int:product_id>/images/",
        AdminProductImageCreateView.as_view(),
        name="admin-product-image-create",
    ),
    path(
        "admin/products/<int:product_id>/images/<int:image_id>/",
        AdminProductImageDestroyView.as_view(),
        name="admin-product-image-destroy",
    ),
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin-category-list"),
    path(
        "admin/categories/<int:pk>/",
        AdminCategoryDetailView.as_view(),
        name="admin-category-detail",
    ),
    path("admin/stats/", AdminStatsView.as_view(), name="admin-stats"),
]

urlpatterns = public_urlpatterns + admin_urlpatterns
