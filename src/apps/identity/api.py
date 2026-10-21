from django.contrib.auth import login as session_login
from django.contrib.auth import logout as session_logout
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.identity.models import Address, Customer
from apps.identity.services.addresses import (
    create_address,
    delete_address,
    get_address,
    list_addresses,
    update_address,
)
from apps.identity.services.authentication import (
    authenticate_credentials,
    issue_api_token,
    revoke_api_token,
)
from apps.identity.services.passwords import request_password_reset, reset_password
from apps.identity.services.registration import register_customer
from apps.identity.services.verification import verify_email
from core.exceptions import NotFoundError


class HasPerm(BasePermission):
    perm_code = None

    def has_permission(self, request, view) -> bool:
        user = request.user
        if user is None or not user.is_authenticated:
            return False
        return user.has_perm(self.perm_code)


def has_perm(perm_code: str) -> type[HasPerm]:
    return type("HasPerm", (HasPerm,), {"perm_code": perm_code})


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(required=False, allow_blank=True, default="")
    last_name = serializers.CharField(required=False, allow_blank=True, default="")


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    password = serializers.CharField(min_length=8, write_only=True)


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.UUIDField()


class CustomerSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)

    class Meta:
        model = Customer
        fields = ["id", "email", "first_name", "last_name", "phone"]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        instance = super().update(instance, validated_data)
        for field, value in user_data.items():
            setattr(instance.user, field, value)
        instance.user.save(update_fields=["first_name", "last_name"])
        return instance


class AddressSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    is_default = serializers.BooleanField(required=False)

    class Meta:
        model = Address
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "country",
            "state",
            "city",
            "postal_code",
            "address_line",
            "is_default",
        ]
        read_only_fields = ["id"]


def _current_customer(request) -> Customer:
    customer = Customer.objects.filter(user=request.user).first()
    if customer is None:
        raise NotFoundError("Customer profile not found", code="identity.no_customer_profile")
    return customer


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        revoke_api_token(request.user)
        # Also end the Django session so server-rendered pages reflect logout.
        session_logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(APIView):
    throttle_scope = "auth"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = register_customer(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        if not result:
            raise result.error
        user = result.value
        return Response(
            {"id": str(user.id), "email": user.email},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    throttle_scope = "auth"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate_credentials(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            request=request,
        )
        # Establish a Django session too, so server-rendered storefront pages
        # share the authenticated state with the SPA.
        session_login(
            request._request, user, backend="django.contrib.auth.backends.ModelBackend"
        )
        token = issue_api_token(user)
        return Response({"token": token.key, "user_id": str(user.id)})


class PasswordResetRequestView(APIView):
    throttle_scope = "auth"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(serializer.validated_data["email"])
        return Response({"detail": "If the email exists, a reset was requested."})


class PasswordResetConfirmView(APIView):
    throttle_scope = "auth"
    throttle_classes = [ScopedRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reset_password(
            serializer.validated_data["token"], serializer.validated_data["password"]
        )
        return Response({"detail": "Password has been reset."})


class VerifyEmailView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = verify_email(serializer.validated_data["token"])
        if user is None:
            raise NotFoundError("Invalid or expired token", code="identity.invalid_verification_token")
        return Response({"detail": "Email verified.", "email": user.email})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        customer = Customer.objects.filter(user=request.user).first()
        serializer = CustomerSerializer(customer)
        return Response(serializer.data)


class MeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        customer = Customer.objects.filter(user=request.user).first()
        if customer is None:
            raise NotFoundError("Customer profile not found", code="identity.no_customer_profile")
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class AddressListCreateView(APIView):
    """The signed-in customer's own saved addresses (FR-CUST-002)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        customer = _current_customer(request)
        return Response(AddressSerializer(list_addresses(customer), many=True).data)

    def post(self, request, *args, **kwargs):
        customer = _current_customer(request)
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        is_default = bool(data.pop("is_default", False))
        address = create_address(customer, is_default=is_default, **data)
        return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    """One of the signed-in customer's own saved addresses (FR-CUST-002)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, address_id, *args, **kwargs):
        customer = _current_customer(request)
        address = get_address(customer, address_id)
        return Response(AddressSerializer(address).data)

    def patch(self, request, address_id, *args, **kwargs):
        customer = _current_customer(request)
        address = get_address(customer, address_id)
        serializer = AddressSerializer(address, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        is_default = data.pop("is_default", None)
        address = update_address(address, is_default=is_default, **data)
        return Response(AddressSerializer(address).data)

    def delete(self, request, address_id, *args, **kwargs):
        customer = _current_customer(request)
        address = get_address(customer, address_id)
        delete_address(address)
        return Response(status=status.HTTP_204_NO_CONTENT)
