from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Permite acceder a items de un diccionario en templates"""
    if dictionary is None:
        return None
    return dictionary.get(key)
