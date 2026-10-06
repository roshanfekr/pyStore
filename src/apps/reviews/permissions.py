from apps.identity.services.roles import ensure_permission

REVIEWS_PERMISSIONS = [
    ("reviews.review.moderate", "Moderate reviews"),
]


def ensure_reviews_permissions() -> None:
    for codename, display_name in REVIEWS_PERMISSIONS:
        ensure_permission(codename, display_name=display_name, source="core")
