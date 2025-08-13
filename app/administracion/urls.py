from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_administracion, name='home_administracion'),
]