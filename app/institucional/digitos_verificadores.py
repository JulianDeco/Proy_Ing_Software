import hashlib
from django.apps import apps
from django.db.models import Sum

class GestorDigitosVerificadores:
    """
    Gestor para el cálculo y verificación de Dígitos Verificadores Horizontales (DVH)
    y Verticales (DVV) para garantizar la integridad de los datos.
    """

    @staticmethod
    def calcular_hash(cadena):
        """Calcula el hash SHA256 de una cadena."""
        return hashlib.sha256(cadena.encode('utf-8')).hexdigest()

    @staticmethod
    def calcular_dvh(instancia, campos_criticos):
        """
        Calcula el DVH para una instancia de modelo basada en sus campos críticos.
        
        Args:
            instancia: Objeto del modelo (e.g., Calificacion).
            campos_criticos: Lista de nombres de campos a incluir (e.g., ['nota', 'tipo']).
        
        Returns:
            str: Hash SHA256 del registro.
        """
        valor_concatenado = ""
        for campo in campos_criticos:
            valor = getattr(instancia, campo)
            # Manejo de None y conversión a string
            if valor is None:
                valor_str = "None"
            else:
                valor_str = str(valor)
            valor_concatenado += valor_str
        
        # Agregar ID si existe para unicidad posicional (evitar intercambio de registros iguales)
        if instancia.pk:
            valor_concatenado += str(instancia.pk)
            
        return GestorDigitosVerificadores.calcular_hash(valor_concatenado)

    @staticmethod
    def calcular_dvv(modelo_nombre, app_label='academico'):
        """
        Calcula el DVV para una tabla completa sumando/concatenando todos los DVH.
        
        Args:
            modelo_nombre: Nombre del modelo (e.g., 'Calificacion').
            app_label: Nombre de la app.
            
        Returns:
            str: Hash SHA256 de todos los DVH concatenados.
        """
        Modelo = apps.get_model(app_label, modelo_nombre)
        
        # Obtener todos los DVH ordenados por PK para consistencia
        dvhs = Modelo.objects.all().order_by('pk').values_list('dvh', flat=True)
        
        concatenacion_total = ""
        for dvh in dvhs:
            if dvh:
                concatenacion_total += dvh
                
        return GestorDigitosVerificadores.calcular_hash(concatenacion_total)

    @staticmethod
    def actualizar_dvv(modelo_nombre, app_label='academico'):
        """Calcula y actualiza el registro DVV en la base de datos."""
        from institucional.models import DigitoVerificadorVertical
        
        nuevo_dvv = GestorDigitosVerificadores.calcular_dvv(modelo_nombre, app_label)
        tabla_id = f"{app_label}.{modelo_nombre}"
        
        obj, created = DigitoVerificadorVertical.objects.get_or_create(tabla=tabla_id)
        obj.dvv = nuevo_dvv
        obj.save()
        return nuevo_dvv

    @staticmethod
    def verificar_integridad_instancia(instancia, campos_criticos):
        """Verifica si el DVH de una instancia coincide con el calculado."""
        if not hasattr(instancia, 'dvh'):
            return False # No tiene DVH implementado
            
        dvh_calculado = GestorDigitosVerificadores.calcular_dvh(instancia, campos_criticos)
        return instancia.dvh == dvh_calculado

    @staticmethod
    def verificar_integridad_tabla(modelo_nombre, app_label='academico'):
        """
        Verifica la integridad vertical de una tabla.
        Compara el DVV almacenado con el recalculado.
        """
        from institucional.models import DigitoVerificadorVertical
        
        tabla_id = f"{app_label}.{modelo_nombre}"
        try:
            dvv_registrado = DigitoVerificadorVertical.objects.get(tabla=tabla_id).dvv
        except DigitoVerificadorVertical.DoesNotExist:
            return False, "No existe DVV registrado para esta tabla."
            
        dvv_calculado = GestorDigitosVerificadores.calcular_dvv(modelo_nombre, app_label)
        
        if dvv_registrado == dvv_calculado:
            return True, "Integridad Vertical OK"
        else:
            return False, "Fallo de Integridad Vertical: El DVV calculado no coincide con el registrado."
