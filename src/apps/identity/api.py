from rest_framework import serializers, status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.identity.models import Customer
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


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        revoke_api_token(request.user)
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
