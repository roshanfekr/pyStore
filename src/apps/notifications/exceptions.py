from core.exceptions import ApplicationError


class NotificationError(ApplicationError):
    message = "Notification error"
    code = "notifications_error"
