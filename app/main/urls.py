from django.contrib import admin
from django.urls import include, path

from main.views import vista_prueba

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('prueba/', vista_prueba),
    
    path('institucional/', include('institucional.urls')),
    path('academico/', include('academico.urls')),
    path('administracion/', include('administracion.urls')),
]