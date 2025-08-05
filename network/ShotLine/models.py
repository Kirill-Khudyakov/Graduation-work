from django.db import models
from django.contrib.auth import get_user_model
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


User = get_user_model()
geolocator = Nominatim(user_agent='my_social_network_ShotLine')


def get_coordinates(location_name):
    """
    Получаем географические координаты (широту и долготу) по названию места.
    Используем сервис Nominatim для геокодирования.
    """
    try:
        location = geolocator.geocode(location_name)
        if location:
            return (location.latitude, location.longitude)
    except (GeocoderTimedOut, GeocoderServiceError):
        # В случае таймаута или ошибки сервиса возвращаем None
        pass
    return (None, None)


def get_location_name(latitude, longitude):
    """
    Получаем название места (адрес) по географическим координатам.
    Используем сервис Nominatim для обратного геокодирования.
    """
    try:
        location = geolocator.reverse((latitude, longitude), exactly_one=True)
        if location:
            return location.address
    except (GeocoderTimedOut, GeocoderServiceError):
        # В случае таймаута или ошибки сервиса возвращаем None
        pass
    return None


class Post(models.Model):
    """
    Модель поста в социальной сети.
    Атрибуты:
        author (ForeignKey): Автор поста, связанный с моделью пользователя.
        text (TextField): Текстовое содержимое поста.
        created_at (DateTimeField): Дата и время создания поста.
        location_name (CharField): Название места или адрес, связанный с постом.
        latitude (DecimalField): Широта геолокации.
        longitude (DecimalField): Долгота геолокации.
    Методы:
        save: Переопределён для автоматического получения координат по location_name.
        location_address (property): Возвращает адрес по координатам или location_name.
        likes_count (property): Количество лайков у поста.
        image_url (property): URL первого изображения поста, если есть.
        __str__: Человекочитаемое представление объекта.
    """
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts', verbose_name='Автор')
    text = models.TextField(verbose_name='Текст поста')
    created_at = models.DateTimeField( auto_now_add=True, verbose_name='Дата создания')
    location_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name='Местоположение (адрес, название)',
        help_text='Введите адрес или название места для автоматического определения координат'
        )  
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6, 
        blank=True, 
        null=True, 
        verbose_name='Широта'
        )  
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='Долгота'
        )

    class Meta:
        verbose_name = 'Пост'
        verbose_name_plural = 'Посты'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        """
        Переопределённый метод сохранения.
        Если указано location_name, но координаты отсутствуют,
        пытается получить широту и долготу через геокодер.
        """
        if self.location_name and (self.latitude is None or self.longitude is None):
            lat, lon = get_coordinates(self.location_name)
            if lat is not None and lon is not None:
                self.latitude = lat
                self.longitude = lon
        super().save(*args, **kwargs)

    @property
    def location_address(self):
        """
        Возвращает полный адрес по координатам, если они есть.
        Если координаты отсутствуют или обратное геокодирование не удалось,
        возвращает значение location_name или пустую строку.
        """
        if self.latitude and self.longitude:
            address = get_location_name(self.latitude, self.longitude)
            if address:
                return address
        return self.location_name or ''
    
    @property
    #  Количество лайков, связанных с постом.
    def likes_count(self):
        return self.likes.count()
    
    @property
    #  URL первого изображения, связанного с постом.
    def image_url(self):
        if self.images.exists():
            return self.images.first().image.url
        return None

    def __str__(self):
        #  Возвращает первые 50 символов текста с указанием автора и ID поста.
        preview = self.text[:50] + ('...' if len(self.text) > 50 else '')
        return f'Пост #{self.id} от {self.author.username}: "{preview}"'


class PostImage(models.Model):
    """
    Модель изображения, связанного с постом.
    Атрибуты:
        post (ForeignKey): Связанный пост.
        image (ImageField): Изображение.
        created_at (DateTimeField): Дата и время добавления изображения.
    Методы:
        __str__: Человекочитаемое представление объекта.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images', verbose_name='Пост')
    image = models.ImageField(upload_to='posts/images/%Y/%m/%d/', verbose_name='Изображение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Изображение поста'
        verbose_name_plural = 'Изображения постов'
        ordering = ['-created_at']

    def __str__(self):
        #  Строка с указанием ID изображения и связанного поста.
        return f'Изображение #{self.id} для поста #{self.post.id}'


class Like(models.Model):
    """
    Модель лайка, связанного с постом и пользователем.
    Атрибуты:
        post (ForeignKey): Пост, которому поставлен лайк.
        user (ForeignKey): Пользователь, поставивший лайк.
        created_at (DateTimeField): Дата и время создания лайка.
    Метаданные:
        unique_together: Обеспечивает уникальность сочетания поста и пользователя (один лайк на пост от пользователя).  
    Методы:
        __str__: Человекочитаемое представление объекта.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes', verbose_name='Пост')
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='likes', verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    

    class Meta:
        unique_together = ('post', 'user')
        verbose_name = 'Лайк'
        verbose_name_plural = 'Лайки'
        ordering = ['-created_at']

    def __str__(self):
        #  Строка с указанием пользователя и поста.
        return f'Лайк от {self.user.username} к посту #{self.post.id}'


class Comment(models.Model):
    """
    Модель комментария к посту.
    Атрибуты:
        post (ForeignKey): Пост, к которому относится комментарий.
        author (ForeignKey): Автор комментария.
        text (TextField): Текст комментария.
        created_at (DateTimeField): Дата и время создания комментария.
    Методы:
        __str__: Человекочитаемое представление объекта.
    """
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', verbose_name='Пост')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments', verbose_name='Автор комментария')
    text = models.TextField(verbose_name='Текст комментария')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']

    def __str__(self):
        #  Возвращает первые 50 символов текста, имя автора и дату создания.
        preview = self.text[:50] + ('...' if len(self.text) > 50 else '')
        created = self.created_at.strftime('%Y-%m-%d %H:%M')
        return f'Комментарий от {self.author.username} ({created}): {preview}'
