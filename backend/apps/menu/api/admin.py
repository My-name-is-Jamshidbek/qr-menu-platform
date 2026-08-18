"""Staff-facing menu CRUD.

Reached only from the Next.js server with a bearer token; the browser never calls it.
Every endpoint here requires a staff role, and the write paths are the ones the cache
invalidation signals hang off.
"""

from datetime import timedelta

from django.db.models import Count, QuerySet
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.generics import (
    CreateAPIView,
    DestroyAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStaffRole
from apps.common.enums import Language
from apps.common.serializers import ErrorSerializer
from apps.menu.models import Category, Product, ProductImage
from apps.menu.serializers import (
    AdminCategorySerializer,
    AdminProductImageSerializer,
    AdminProductSerializer,
    ProductImageUploadSerializer,
    StatsSerializer,
)
from apps.tables.models import TableScan

STATS_WINDOW_DAYS = 7


class CategoryInUse(APIException):
    """409 rather than a 500 from the model's PROTECT constraint."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "This category still has products and cannot be deleted."
    default_code = "category_in_use"


class StaffApiMixin:
    permission_classes = [IsStaffRole]


@extend_schema(tags=["admin-menu"])
class AdminProductListCreateView(StaffApiMixin, ListCreateAPIView):
    serializer_class = AdminProductSerializer

    def get_queryset(self) -> QuerySet[Product]:
        queryset = (
            Product.objects.all()
            .select_related("category")
            .prefetch_related("translations", "images")
        )
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset


@extend_schema(tags=["admin-menu"])
class AdminProductDetailView(StaffApiMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = AdminProductSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Product]:
        return (
            Product.objects.all()
            .select_related("category")
            .prefetch_related("translations", "images")
        )


@extend_schema(
    tags=["admin-menu"],
    summary="Attach a photo to a product",
    request={"multipart/form-data": ProductImageUploadSerializer},
    responses={201: ProductImageUploadSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
)
class AdminProductImageCreateView(StaffApiMixin, CreateAPIView):
    """Multipart upload; the model converts the original to WebP at three widths."""

    serializer_class = ProductImageUploadSerializer

    def get_queryset(self) -> QuerySet[ProductImage]:
        return ProductImage.objects.filter(product_id=self.kwargs["product_id"])

    def perform_create(self, serializer: ProductImageUploadSerializer) -> None:
        product = Product.objects.filter(pk=self.kwargs["product_id"]).first()
        if product is None:
            raise Http404("No product matches the given id.")
        serializer.save(product=product)


@extend_schema(tags=["admin-menu"], summary="Remove a photo and its derivatives")
class AdminProductImageDestroyView(StaffApiMixin, DestroyAPIView):
    serializer_class = AdminProductImageSerializer
    lookup_url_kwarg = "image_id"

    def get_queryset(self) -> QuerySet[ProductImage]:
        return ProductImage.objects.filter(product_id=self.kwargs["product_id"])


@extend_schema(tags=["admin-menu"])
class AdminCategoryListCreateView(StaffApiMixin, ListCreateAPIView):
    serializer_class = AdminCategorySerializer

    def get_queryset(self) -> QuerySet[Category]:
        return (
            Category.objects.all()
            .prefetch_related("translations")
            .annotate(product_count=Count("products"))
        )


@extend_schema(
    tags=["admin-menu"],
    responses={
        204: OpenApiResponse(description="Deleted."),
        409: OpenApiResponse(response=ErrorSerializer, description="Products reference it."),
    },
)
class AdminCategoryDetailView(StaffApiMixin, RetrieveUpdateDestroyAPIView):
    serializer_class = AdminCategorySerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Category]:
        return (
            Category.objects.all()
            .prefetch_related("translations")
            .annotate(product_count=Count("products"))
        )

    def perform_destroy(self, instance: Category) -> None:
        if instance.products.exists() or instance.children.exists():
            raise CategoryInUse()
        instance.delete()


@extend_schema(
    tags=["admin-menu"],
    summary="Counters for the admin dashboard",
    responses={200: StatsSerializer},
)
class AdminStatsView(StaffApiMixin, APIView):
    def get(self, request: Request) -> Response:
        since = timezone.now() - timedelta(days=STATS_WINDOW_DAYS)
        incomplete = Product.objects.annotate(
            translated_languages=Count("translations__language", distinct=True)
        ).filter(translated_languages__lt=len(Language.values))
        payload = {
            "product_count": Product.objects.count(),
            "available_product_count": Product.objects.filter(is_available=True).count(),
            "category_count": Category.objects.count(),
            "missing_translation_count": incomplete.count(),
            "scans_last_7_days": TableScan.objects.filter(scanned_at__gte=since).count(),
        }
        return Response(StatsSerializer(payload).data)
