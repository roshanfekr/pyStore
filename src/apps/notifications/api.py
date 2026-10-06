from rest_framework import serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from apps.notifications.models import WebhookDeliveryLog, WebhookEndpoint
from core.api.filters import QueryParamFilterMixin


class WebhookEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEndpoint
        fields = [
            "id", "target_url", "secret", "event_names", "is_active",
            "max_retries", "description", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_event_names(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("event_names must be a non-empty list of event names.")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError("Event names must be non-empty strings.")
        return value

    def validate_secret(self, value):
        if value and len(value) < 16:
            raise serializers.ValidationError("Secret must be at least 16 characters long.")
        return value

    def validate_target_url(self, value):
        from core.security.ssrf import validate_public_url

        validate_public_url(value)
        return value


class WebhookDeliveryLogSerializer(serializers.ModelSerializer):
    target_url = serializers.CharField(source="endpoint.target_url", read_only=True)

    class Meta:
        model = WebhookDeliveryLog
        fields = [
            "id", "endpoint", "target_url", "event_name", "attempt",
            "successful", "status_code", "error", "duration_ms", "created_at",
        ]


class WebhookEndpointViewSet(ModelViewSet):
    """CRUD management of webhook endpoints (staff only)."""

    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAdminUser]
    queryset = WebhookEndpoint.objects.all()
    lookup_field = "pk"

    query_filters = {"is_active": "is_active"}
    ordering_fields = ("created_at", "target_url")
    search_fields = ("target_url", "description")
    default_ordering = "-created_at"

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        event = self.request.query_params.get("event")
        if event:
            matching = [endpoint.pk for endpoint in queryset if endpoint.matches_event(event)]
            queryset = queryset.filter(pk__in=matching)
        return queryset


class WebhookDeliveryLogViewSet(QueryParamFilterMixin, ReadOnlyModelViewSet):
    """Read-only access to the webhook delivery log (staff only)."""

    serializer_class = WebhookDeliveryLogSerializer
    permission_classes = [IsAdminUser]
    queryset = WebhookDeliveryLog.objects.select_related("endpoint")

    query_filters = {
        "event": "event_name",
        "successful": "successful",
        "endpoint": "endpoint__pk",
    }
    ordering_fields = ("created_at", "event_name", "attempt")
    default_ordering = "-created_at"
