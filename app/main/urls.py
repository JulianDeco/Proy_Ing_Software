from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from main.views import LoginEmailView, home, logout_view, redirect_based_group

admin.site.site_title = "Sitio de administración - Sistema de administración"
admin.site.site_header = "Administración de sistema educativo"
admin.site.index_title = "Sitio de administración"

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('redirect', redirect_based_group, name='redirect_login'),
    path('logout', logout_view, name='logout'),
    path('login', LoginEmailView.as_view(), name='login'),

    path('', home, name='home'),
    
    path('institucional/', include('institucional.urls')),
    path('academico/', include('academico.urls')),
    path('administracion/', include('administracion.urls')),

    path("change-password", auth_views.PasswordChangeView.as_view()),
    path('password-recovery', auth_views.PasswordResetView.as_view()),

]