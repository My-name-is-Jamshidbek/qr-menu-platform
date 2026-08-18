from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """`?page=&page_size=` paging as described in the API contract."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
