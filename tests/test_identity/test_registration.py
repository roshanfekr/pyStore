import pytest

from apps.identity.events import CustomerRegistered
from apps.identity.models import Customer
from apps.identity.services.registration import RegistrationService, register_customer
from core.events import dispatcher
from core.exceptions import ConflictError, ValidationError

pytestmark = [pytest.mark.django_db]

VALID_PASSWORD = "Str0ng!Passw0rd"


def test_register_customer_creates_user_profile_and_event():
    service = RegistrationService()
    result = service.run(email="new@example.com", password=VALID_PASSWORD, first_name="Ali")

    assert result.success
    user = result.value
    assert Customer.objects.filter(user=user).exists()
    events = service.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], CustomerRegistered)
    assert events[0].email == "new@example.com"


def test_register_customer_helper_dispatches_event():
    received = []

    def handler(event):
        received.append(event)

    dispatcher.subscribe(CustomerRegistered, handler)
    try:
        result = register_customer(email="dispatch@example.com", password=VALID_PASSWORD)
    finally:
        dispatcher.unsubscribe(CustomerRegistered, handler)

    assert result.success
    assert len(received) == 1
    assert received[0].user_id == str(result.value.id)


def test_duplicate_email_conflict():
    service = RegistrationService()
    service.run(email="same@example.com", password=VALID_PASSWORD)

    second = RegistrationService()
    result = second.run(email="same@example.com", password=VALID_PASSWORD)

    assert result.success is False
    assert result.error.code == "identity.email_taken"
    assert isinstance(result.error, ConflictError)


@pytest.mark.parametrize(
    "weak",
    ["short", "alllowercase1!", "NOLOWERCASE1!", "12345678", "NoSpecial123"],
)
def test_weak_passwords_rejected_with_details(weak):
    service = RegistrationService()
    result = service.run(email=f"weak{weak[:4]}@example.com", password=weak)

    assert result.success is False
    assert isinstance(result.error, ValidationError)
    assert result.error.details and result.error.details["password"]
