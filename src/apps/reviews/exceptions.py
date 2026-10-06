from core.exceptions import ApplicationError


class ReviewError(ApplicationError):
    message = "Review error"
    code = "reviews_error"
