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

    path('', redirect_based_group, name='home'),

    path('institucional/', include('institucional.urls')),
    path('academico/', include('academico.urls')),
    path('administracion/', include('administracion.urls')),

    # Cambio de contraseña (usuario autenticado)
    path('cambiar-contrasena/', auth_views.PasswordChangeView.as_view(
        template_name='security/password_change_form.html',
        success_url='/cambiar-contrasena/completado/'
    ), name='password_change'),
    path('cambiar-contrasena/completado/', auth_views.PasswordChangeDoneView.as_view(
        template_name='security/password_change_done.html'
    ), name='password_change_done'),

    # Reset de contraseña (usuario no autenticado)
    path('restablecer-contrasena/', auth_views.PasswordResetView.as_view(
        template_name='security/password_reset_form.html',
        email_template_name='security/password_reset_email.html',
        subject_template_name='security/password_reset_subject.txt',
        success_url='/restablecer-contrasena/enviado/'
    ), name='password_reset'),
    path('restablecer-contrasena/enviado/', auth_views.PasswordResetDoneView.as_view(
        template_name='security/password_reset_done.html'
    ), name='password_reset_done'),
    path('restablecer-contrasena/confirmar/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='security/password_reset_confirm.html',
        success_url='/restablecer-contrasena/completado/'
    ), name='password_reset_confirm'),
    path('restablecer-contrasena/completado/', auth_views.PasswordResetCompleteView.as_view(
        template_name='security/password_reset_complete.html'
    ), name='password_reset_complete'),

]