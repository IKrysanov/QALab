class WebClientException(Exception):
    """Базовое исключение для Web клиента"""
    pass

class NavigationException(WebClientException):
    """Исключение навигации"""
    pass

class ElementNotFoundException(WebClientException):
    """Исключение ненайденного элемента"""
    pass