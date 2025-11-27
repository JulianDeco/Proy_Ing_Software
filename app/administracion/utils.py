import os
import shutil
import datetime
import base64
import hashlib
from django.conf import settings
from django.http import HttpResponse, FileResponse
from django.core.management import call_command
from io import BytesIO
import zipfile

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generar_clave_encriptacion(password: str, salt: bytes = None) -> tuple:
    """
    Genera una clave de encriptación a partir de una contraseña.

    Args:
        password: Contraseña para derivar la clave
        salt: Salt para la derivación (si no se proporciona, se genera uno nuevo)

    Returns:
        tuple: (clave_fernet, salt)
    """
    if salt is None:
        salt = os.urandom(16)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return Fernet(key), salt


def encriptar_datos(datos: bytes, password: str) -> bytes:
    """
    Encripta datos usando una contraseña.

    Args:
        datos: Datos en bytes a encriptar
        password: Contraseña para la encriptación

    Returns:
        bytes: Datos encriptados con el salt prepended
    """
    fernet, salt = generar_clave_encriptacion(password)
    datos_encriptados = fernet.encrypt(datos)
    # Prepend salt a los datos encriptados (16 bytes de salt + datos)
    return salt + datos_encriptados


def desencriptar_datos(datos_encriptados: bytes, password: str) -> bytes:
    """
    Desencripta datos usando una contraseña.

    Args:
        datos_encriptados: Datos encriptados (salt + datos)
        password: Contraseña para la desencriptación

    Returns:
        bytes: Datos desencriptados

    Raises:
        ValueError: Si la contraseña es incorrecta o los datos están corruptos
    """
    # Extraer salt (primeros 16 bytes)
    salt = datos_encriptados[:16]
    datos = datos_encriptados[16:]

    try:
        fernet, _ = generar_clave_encriptacion(password, salt)
        return fernet.decrypt(datos)
    except Exception as e:
        raise ValueError("Contraseña incorrecta o archivo corrupto") from e

def crear_backup_completo(password: str = None):
    """
    Crea un backup completo del sistema incluyendo:
    - Base de datos (dumpdata JSON)
    - Archivos media (si existen)
    - Configuración importante

    Args:
        password: Si se proporciona, el backup será encriptado con esta contraseña

    Returns:
        tuple: (buffer, filename) - El buffer con el archivo y su nombre
    """
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_sistema_{timestamp}'
    encriptado = password is not None and len(password) > 0

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
Encriptado: {'Sí' if encriptado else 'No'}

CONTENIDO:
- database_backup.json: Backup completo de la base de datos
- Base de datos SQLite: {settings.DATABASES['default']['NAME']}

INSTRUCCIONES DE RESTAURACIÓN:
1. {'Usar la contraseña proporcionada al crear el backup' if encriptado else 'Descomprimir este archivo'}
2. Restaurar desde el panel de administración
3. O manualmente: python manage.py loaddata database_backup.json

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

    # Si se proporcionó contraseña, encriptar el backup
    if encriptado:
        datos_zip = zip_buffer.getvalue()
        datos_encriptados = encriptar_datos(datos_zip, password)
        encrypted_buffer = BytesIO(datos_encriptados)
        encrypted_buffer.seek(0)
        return encrypted_buffer, f'{backup_name}.zip.enc'

    return zip_buffer, f'{backup_name}.zip'

def restaurar_backup(archivo, password: str = None):
    """
    Restaura un backup del sistema desde un archivo ZIP (puede estar encriptado)

    Args:
        archivo: Archivo uploadado con el backup (ZIP o ZIP encriptado)
        password: Contraseña si el backup está encriptado

    Returns:
        tuple: (success: bool, mensaje: str)
    """
    import tempfile
    import json
    from django.core.management import call_command
    from django.db import connection

    try:
        # Leer el contenido del archivo
        archivo_contenido = archivo.read()
        archivo_nombre = archivo.name if hasattr(archivo, 'name') else ''

        # Verificar si está encriptado (extensión .enc o proporcionaron contraseña)
        es_encriptado = archivo_nombre.endswith('.enc') or (password and len(password) > 0)

        if es_encriptado:
            if not password:
                return False, "El archivo está encriptado. Debe proporcionar la contraseña."

            try:
                # Desencriptar el archivo
                archivo_contenido = desencriptar_datos(archivo_contenido, password)
            except ValueError as e:
                return False, str(e)

        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            # Crear un BytesIO con el contenido (desencriptado si aplica)
            zip_buffer = BytesIO(archivo_contenido)

            try:
                # Extraer el ZIP
                with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
            except zipfile.BadZipFile:
                return False, "El archivo no es un ZIP válido. Verifique que el archivo y la contraseña sean correctos."

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

            return True, "Backup restaurado exitosamente. Se han recuperado todos los datos."

    except Exception as e:
        return False, f"Error al restaurar el backup: {str(e)}"
