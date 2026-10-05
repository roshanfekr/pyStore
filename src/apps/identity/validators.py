from django.core.exceptions import ValidationError


class ComplexPasswordValidator:
    """Requires upper, lower, digit and special character."""

    SPECIALS = "!@#$%^&*()-_=+[]{}|;:,.<>?"

    def validate(self, password, user=None):
        errors = []
        if not any(c.isupper() for c in password):
            errors.append("Password must contain an uppercase letter.")
        if not any(c.islower() for c in password):
            errors.append("Password must contain a lowercase letter.")
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain a digit.")
        if not any(c in self.SPECIALS for c in password):
            errors.append("Password must contain a special character.")
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return "Your password must contain upper and lower case letters, a digit and a special character."
