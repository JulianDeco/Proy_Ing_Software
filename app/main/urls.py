from django.contrib import admin
from django.urls import include, path

from main.views import dashboard_profesores, home, login

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('login/', login, name='login'),
    path('', home, name='home'),
    path('profesores/', dashboard_profesores, name='dashboard_profesores'),
    
    path('institucional/', include('institucional.urls')),
    path('academico/', include('academico.urls')),
    path('administracion/', include('administracion.urls')),
]