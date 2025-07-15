from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("administracion/", include("administracion.urls")),
    path("admin/", admin.site.urls),
]