"""Excepciones personalizadas para el módulo académico"""


class AcademicoException(Exception):
    """Excepción base para errores académicos"""
    pass


class TipoCalificacionInvalidoError(AcademicoException):
    """Se lanza cuando el tipo de calificación no es válido"""
    pass


class RangoCalificacionInvalidoError(AcademicoException):
    """Se lanza cuando la calificación está fuera del rango permitido"""
    pass


class CapacidadExcedidaError(AcademicoException):
    """Se lanza cuando se intenta inscribir un alumno y el cupo está completo"""
    pass


class CorrelatividadNoAprobadaError(AcademicoException):
    """Se lanza cuando un alumno intenta inscribirse sin haber aprobado las correlativas"""
    pass


class AsistenciaNoExisteError(AcademicoException):
    """Se lanza cuando no existe un registro de asistencia para la fecha especificada"""
    pass


class FechaNoClaseError(AcademicoException):
    """Se lanza cuando se intenta registrar asistencia en un día que no es de clase"""
    pass
