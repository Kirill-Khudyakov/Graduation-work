from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Кастомное разрешение для проверки прав доступа к объекту.
    Позволяет безопасные методы (GET, HEAD, OPTIONS) всем пользователям,
    а методы изменения (POST, PUT, PATCH, DELETE) — только автору объекта.
    Объект должен иметь атрибут 'author' или 'user' для проверки авторства.
    """

    def has_object_permission(self, request, view, obj):
        """
        Проверяет, разрешено ли пользователю выполнять действие с объектом.
        Args:
            request: HTTP-запрос.
            view: Вьюха, обрабатывающая запрос.
            obj: Объект модели, к которому запрашивается доступ.
        Returns:
            bool: True, если метод безопасный (чтение) или если пользователь — автор объекта.
        """
        # Разрешаем безопасные методы без ограничений
        if request.method in permissions.SAFE_METHODS:
            return True

        # Получаем автора объекта (если есть) из атрибутов 'author' или 'user'
        author = getattr(obj, 'author', None) or getattr(obj, 'user', None)

        # Разрешаем только автору объекта изменять его
        return author == request.user