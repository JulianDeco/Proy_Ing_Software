"""
Comando personalizado para cargar fixtures deshabilitando temporalmente
las restricciones de clave foránea en SQLite.

Esto soluciona el problema de "FOREIGN KEY constraint failed" que ocurre
cuando el orden de inserción de datos viola las restricciones FK.
"""
from django.core.management.commands.loaddata import Command as LoadDataCommand
from django.db import connections, transaction


class Command(LoadDataCommand):
    help = 'Carga fixtures deshabilitando las restricciones de clave foránea en SQLite'

    def handle(self, *fixture_labels, **options):
        """
        Sobrescribe el método handle del comando loaddata original
        para deshabilitar FK constraints dentro del bloque transaccional.
        """
        self.ignore = options["ignore"]
        self.using = options["database"]
        self.app_label = options["app_label"]
        self.verbosity = options["verbosity"]

        from django.core.management.utils import parse_apps_and_model_labels
        self.excluded_models, self.excluded_apps = parse_apps_and_model_labels(
            options["exclude"]
        )
        self.format = options["format"]

        connection = connections[self.using]

        # Usar transacción atómica CON FK constraints deshabilitadas
        with transaction.atomic(using=self.using):
            # Deshabilitar FK constraints DENTRO de la transacción
            with connection.cursor() as cursor:
                cursor.execute('PRAGMA foreign_keys = OFF;')
                if self.verbosity >= 2:
                    self.stdout.write('FK constraints deshabilitadas')

            try:
                # Llamar al método loaddata del padre
                self.loaddata(fixture_labels)
            finally:
                # Re-habilitar FK constraints DENTRO de la transacción
                with connection.cursor() as cursor:
                    cursor.execute('PRAGMA foreign_keys = ON;')
                    if self.verbosity >= 2:
                        self.stdout.write('FK constraints re-habilitadas')

        # Cerrar la conexión si estamos en autocommit
        if transaction.get_autocommit(self.using):
            connections[self.using].close()
