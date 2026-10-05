from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.identity.events import CustomerRegistered
from apps.identity.models import Customer, Role, User
from core.events import dispatcher
from core.exceptions import ConflictError, ValidationError
from core.infrastructure import atomic
from core.services import BaseService

DEFAULT_CUSTOMER_ROLE = "Customers"


def _validate_password(password: str) -> None:
    try:
        django_validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError("Invalid password", details={"password": exc.messages}) from None


class RegistrationService(BaseService):
    def execute(self, email: str, password: str, first_name: str = "", last_name: str = ""):
        _validate_password(password)

        if User.objects.filter(email__iexact=email).exists():
            raise ConflictError(
                "A user with this email already exists", code="identity.email_taken"
            )

        with atomic():
            user = User.objects.create_user(
                email=email, password=password, first_name=first_name, last_name=last_name
            )
            Customer.objects.create(user=user)
            role = Role.objects.filter(name=DEFAULT_CUSTOMER_ROLE).first()
            if role is not None:
                user.roles.add(role)

        self.raise_event(CustomerRegistered(email=user.email, user_id=str(user.id)))
        return user


def register_customer(email: str, password: str, first_name: str = "", last_name: str = ""):
    service = RegistrationService()
    result = service.run(
        email=email, password=password, first_name=first_name, last_name=last_name
    )
    if result:
        dispatcher.dispatch_all(service.collect_events())
    return result
