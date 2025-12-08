from django.contrib import admin
from django.contrib.admin.models import LogEntry

# Este archivo está reservado para configuraciones admin de la app main

# Desregistrar el modelo LogEntry para que no aparezca en el panel de administración
# Se hace esto porque ya existen modelos de auditoría más específicos en la app institucional
try:
    admin.site.unregister(LogEntry)
except admin.sites.AlreadyUnregistered:
    pass # Ya estaba desregistrado, no hacemos nada
