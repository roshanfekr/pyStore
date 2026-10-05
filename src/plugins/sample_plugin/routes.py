from django.http import JsonResponse
from django.urls import path


def hello_view(request):
    return JsonResponse({"message": "Hello from sample plugin"})


urlpatterns = [
    path("sample/hello/", hello_view, name="sample_plugin_hello"),
]
