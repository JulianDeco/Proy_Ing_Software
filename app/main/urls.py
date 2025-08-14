from django.contrib import admin
from django.urls import include, path

from main.views import LoginEmailView, dashboard_profesores, home, logout_view, redirect_based_group

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('redirect', redirect_based_group, name='redirect_login'),
    path('logout', logout_view, name='logout'),
    path('login/', LoginEmailView.as_view(), name='login'),
    
    path('', home, name='home'),
    path('profesores/', dashboard_profesores, name='dashboard_profesores'),
    
    path('institucional/', include('institucional.urls')),
    path('academico/', include('academico.urls')),
    path('administracion/', include('administracion.urls')),
]