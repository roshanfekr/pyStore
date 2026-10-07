from django.utils import translation

from apps.stores.services import get_active_language_code, get_language


class DbLocaleMiddleware:
    """Activates the language chosen by the user (cookie) or the DB default.

    Fully driven by the Languages defined in the admin: any active language
    from the database can be activated, not only codes listed in settings.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings

        cookie_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        code = get_active_language_code(cookie_code)
        language = get_language(code)

        request.LANGUAGE_CODE = code
        if language is not None:
            request.active_language = language
        translation.activate(code)

        response = self.get_response(request)
        response.headers.setdefault("Content-Language", code)
        return response
