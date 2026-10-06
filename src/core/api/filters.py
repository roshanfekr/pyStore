from django.db.models import Q
from rest_framework.exceptions import ValidationError as DRFValidationError


class QueryParamFilterMixin:
    """Query-param filtering and whitelisted sorting for list endpoints.

    Subclasses declare:
      * ``query_filters`` — mapping of query param to queryset filter lookup
        (a lookup of ``None`` means exact match on the param name itself).
      * ``ordering_fields`` — whitelist of orderable fields.
      * ``search_fields`` — fields searched with icontains via ``search`` param.
    """

    query_filters: dict = {}
    ordering_fields: tuple = ()
    search_fields: tuple = ()
    default_ordering: str = "-created_at"

    VALID_OPERATORS = ("gte", "lte", "gt", "lt", "icontains", "in", "isnull")

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        params = self.request.query_params

        for param, lookup in self.query_filters.items():
            if param not in params:
                continue
            raw = params.get(param)
            if raw in (None, ""):
                continue
            if lookup is None:
                lookup = param
            try:
                value = self._cast_filter_value(lookup, raw, queryset)
            except (ValueError, TypeError):
                raise DRFValidationError(
                    f"Invalid filter value for {param!r}"
                ) from None
            queryset = queryset.filter(**{lookup: value})

        search = params.get("search")
        if search and self.search_fields:
            condition = Q()
            for field in self.search_fields:
                condition |= Q(**{f"{field}__icontains": search})
            queryset = queryset.filter(condition)

        return queryset.order_by(*self._resolve_ordering(params))

    def _resolve_ordering(self, params) -> list:
        requested = params.get("ordering", self.default_ordering)
        if not requested:
            requested = self.default_ordering
        allowed = set(self.ordering_fields) | {
            "-" + field for field in self.ordering_fields
        }
        parts = [part for part in requested.split(",") if part in allowed]
        if not parts:
            parts = [self.default_ordering]
        return parts

    def _cast_filter_value(self, lookup: str, raw: str, queryset):
        base_field = lookup
        for operator in self.VALID_OPERATORS:
            if lookup.endswith(f"__{operator}"):
                base_field = lookup[: -(len(operator) + 2)]
                break

        try:
            model_field = queryset.model._meta.get_field(base_field)
        except Exception:
            return raw

        if model_field.get_internal_type() in ("BooleanField", "NullBooleanField"):
            return raw.strip().lower() in ("1", "true", "yes")
        if model_field.get_internal_type() == "DecimalField":
            from decimal import Decimal

            return Decimal(raw)
        return raw
