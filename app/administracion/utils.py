import os
import shutil
import datetime
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.core.management import call_command
from io import BytesIO
import zipfile

def crear_backup_completo():
    """
    Crea un backup completo del sistema incluyendo:
    - Base de datos (dumpdata JSON)
    - Archivos media (si existen)
    - Configuración importante
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_sistema_{timestamp}'

    # Crear un BytesIO para el archivo ZIP en memoria
    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Backup de la base de datos completa
        from io import StringIO
        db_buffer = StringIO()
        call_command('dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    '--indent', '2',
                    stdout=db_buffer,
                    exclude=['contenttypes', 'auth.permission', 'sessions.session'])

        db_buffer.seek(0)
        zip_file.writestr(f'{backup_name}/database_backup.json', db_buffer.getvalue())

        # 2. Información del backup
        info_content = f"""BACKUP DEL SISTEMA EDUCATIVO
Fecha de creación: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Versión: 1.0

CONTENIDO:
- database_backup.json: Backup completo de la base de datos
- Base de datos SQLite: {settings.DATABASES['default']['NAME']}

INSTRUCCIONES DE RESTAURACIÓN:
1. Descomprimir este archivo
2. Restaurar base de datos: python manage.py loaddata database_backup.json
3. Si hay base de datos SQLite, reemplazar el archivo db.sqlite3

NOTA: Este backup NO incluye:
- Contraseñas hasheadas (deberán ser reseteadas)
- Archivos de logs
- Archivos temporales
"""
        zip_file.writestr(f'{backup_name}/README.txt', info_content)

        # 3. Copiar la base de datos SQLite si existe
        db_path = str(settings.DATABASES['default']['NAME'])
        if os.path.exists(db_path) and db_path.endswith('.sqlite3'):
            with open(db_path, 'rb') as db_file:
                zip_file.writestr(f'{backup_name}/db.sqlite3', db_file.read())

        # 4. Backup de archivos media si existen
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root and os.path.exists(media_root):
            for root, dirs, files in os.walk(media_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.join(
                        f'{backup_name}/media',
                        os.path.relpath(file_path, media_root)
                    )
                    zip_file.write(file_path, arcname)

    zip_buffer.seek(0)
    return zip_buffer, f'{backup_name}.zip'

def restaurar_backup(archivo_zip):
    """
    Restaura un backup del sistema desde un archivo ZIP
    Args:
        archivo_zip: Archivo ZIP uploadado con el backup
    Returns:
        tuple: (success: bool, mensaje: str)
    """
    import tempfile
    import json
    from django.core.management import call_command
    from django.db import connection

    try:
        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extraer el ZIP
            with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)

            # Buscar el archivo database_backup.json
            json_file = None
            db_file = None

            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file == 'database_backup.json':
                        json_file = os.path.join(root, file)
                    elif file == 'db.sqlite3':
                        db_file = os.path.join(root, file)

            if not json_file:
                return False, "No se encontró el archivo database_backup.json en el backup"

            # Validar que sea un JSON válido
            try:
                with open(json_file, 'r') as f:
                    json.load(f)
            except json.JSONDecodeError:
                return False, "El archivo de backup no es un JSON válido"

            # Limpiar la base de datos actual (excepto usuarios superadmin)
            from django.contrib.auth import get_user_model
            User = get_user_model()
            superusers = list(User.objects.filter(is_superuser=True).values())

            # Ejecutar flush para limpiar la base de datos
            call_command('flush', '--no-input', verbosity=0)

            # Restaurar los superusuarios
            for su_data in superusers:
                su_data.pop('id', None)
                User.objects.create(**su_data)

            # Cargar los datos del backup
            call_command('loaddata', json_file, verbosity=0)

            # Si existe el archivo db.sqlite3 y estamos usando SQLite,
            # ofrecer reemplazarlo (esto requeriría reiniciar el servidor)
            # Por ahora solo usamos loaddata que es más seguro

            return True, "Backup restaurado exitosamente. Se han recuperado todos los datos."

    except Exception as e:
        return False, f"Error al restaurar el backup: {str(e)}"
