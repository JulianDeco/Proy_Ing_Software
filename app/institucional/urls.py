from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_institucional, name='home_institucional'),
]