"""Public, unauthenticated storefront reads."""

from django.core.cache import cache
from django.db.models import Exists, OuterRef, Q, QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from apps.common.api.language import LANGUAGE_PARAMETER, resolve_language
from apps.common.api.search import fold, folded
from apps.common.serializers import ErrorSerializer
from apps.menu.api.aggregate import build_menu
from apps.menu.api.cache import MENU_CACHE_TTL_SECONDS, menu_cache_key
from apps.menu.models import Product, ProductTranslation
from apps.menu.serializers import (
    MenuSerializer,
    ProductDetailSerializer,
    PublicProductSerializer,
)


@extend_schema(
    tags=["menu"],
    summary="The entire menu in one response",
    parameters=[LANGUAGE_PARAMETER],
    responses={200: MenuSerializer, 400: ErrorSerializer},
)
class MenuView(APIView):
    """`GET /menu/` — cached per language for five minutes, dropped on any menu write."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AnonRateThrottle]

    def get(self, request: Request) -> Response:
        language = resolve_language(request)
        key = menu_cache_key(language)

        payload = cache.get(key)
        if payload is None:
            payload = build_menu(language)
            cache.set(key, payload, MENU_CACHE_TTL_SECONDS)

        return Response(payload)


class PublicProductQuerysetMixin:
    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [AnonRateThrottle]

    def get_serializer_context(self) -> dict:
        context = super().get_serializer_context()
        context["language"] = resolve_language(self.request)
        return context

    def get_queryset(self) -> QuerySet[Product]:
        return (
            Product.objects.filter(is_available=True, category__is_active=True)
            .select_related("category")
            .prefetch_related("translations", "images")
        )


SEARCH_PARAMETER = OpenApiParameter(
    name="search",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Case- and accent-insensitive match on the name or description.",
)

CATEGORY_PARAMETER = OpenApiParameter(
    name="category",
    type=str,
    location=OpenApiParameter.QUERY,
    required=False,
    description="Category slug; a section slug also matches its subsections.",
)


@extend_schema(
    tags=["menu"],
    summary="Paginated product list",
    parameters=[LANGUAGE_PARAMETER, CATEGORY_PARAMETER, SEARCH_PARAMETER],
    responses={200: PublicProductSerializer(many=True), 400: ErrorSerializer},
)
class ProductListView(PublicProductQuerysetMixin, ListAPIView):
    serializer_class = PublicProductSerializer

    def get_queryset(self) -> QuerySet[Product]:
        queryset = super().get_queryset()
        params = self.request.query_params

        category = params.get("category")
        if category:
            queryset = queryset.filter(
                Q(category__slug=category) | Q(category__parent__slug=category)
            )

        search = (params.get("search") or "").strip()
        if search:
            language = resolve_language(self.request)
            term = fold(search)
            # `Exists` rather than a join: a product with a matching name *and*
            # description would otherwise come back twice.
            matches = (
                ProductTranslation.objects.filter(product=OuterRef("pk"), language=language)
                .annotate(folded_name=folded("name"), folded_description=folded("description"))
                .filter(Q(folded_name__contains=term) | Q(folded_description__contains=term))
            )
            queryset = queryset.filter(Exists(matches))

        return queryset


@extend_schema(
    tags=["menu"],
    summary="One product with all of its photos",
    parameters=[LANGUAGE_PARAMETER],
    responses={200: ProductDetailSerializer, 400: ErrorSerializer, 404: ErrorSerializer},
)
class ProductDetailView(PublicProductQuerysetMixin, RetrieveAPIView):
    serializer_class = ProductDetailSerializer
    lookup_field = "slug"
