from django.contrib import admin
from django.urls import include, path

from main.views import home

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('', home, name='home'),
    
    # path('institucional/', include('institucional.urls')),
    path('academico/', include('academico.urls')),
    # path('administracion/', include('administracion.urls')),
]