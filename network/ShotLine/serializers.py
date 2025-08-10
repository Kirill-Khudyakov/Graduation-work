from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import Comment, Like, Post, PostImage
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable


class CommentSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Comment.

    Поля:
        - id: идентификатор комментария (только для чтения)
        - post: внешний ключ на пост, к которому относится комментарий
        - author: автор комментария (только для чтения, устанавливается автоматически)
        - text: текст комментария
        - created_at: дата и время создания комментария (только для чтения)

    При создании комментария автор устанавливается из текущего пользователя запроса.
    """
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())
    created_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'text', 'created_at']

    def create(self, validated_data):
        """
        Переопределение метода создания объекта.
        Устанавливает автора комментария из текущего пользователя запроса.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['author'] = request.user
        return super().create(validated_data)


class PostImageSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели PostImage.

    Поля:
        - id: идентификатор изображения
        - image: файл изображения
    """
    class Meta:
        model = PostImage
        fields = ['id', 'image']


class LikeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Like.

    Поля:
        - id: идентификатор лайка
        - post: внешний ключ на пост, которому поставлен лайк
        - user: пользователь, поставивший лайк (только для чтения, отображается как строка)

    При создании лайка пользователь устанавливается из текущего пользователя запроса.
    """
    user = serializers.StringRelatedField(read_only=True)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())

    class Meta:
        model = Like
        fields = ['id', 'post', 'user']

    def create(self, validated_data):
        """
        Переопределение метода создания объекта.
        Устанавливает пользователя лайка из текущего пользователя запроса.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Post.

    Поля:
        - id: идентификатор поста
        - author: автор поста (только для чтения)
        - text: текст поста
        - created_at: дата и время создания поста (только для чтения)
        - location_name: название или адрес местоположения (только для записи)
        - latitude: широта (только для чтения)
        - longitude: долгота (только для чтения)
        - likes_count: количество лайков (только для чтения)
        - images: связанные изображения поста (только для чтения)
        - image: одно изображение (только для записи, устаревшее поле)
        - uploaded_images: список изображений для загрузки (только для записи)
        - location: словарь с координатами latitude и longitude (только для чтения)

    При создании поста:
        - если задано location_name, пытается получить координаты через геокодер Nominatim
        - загружает связанные изображения из uploaded_images
        - автор устанавливается во вьюхе (не здесь)
    """
    author = serializers.PrimaryKeyRelatedField(read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    images = PostImageSerializer(many=True, read_only=True)
    image = serializers.ImageField(write_only=True, required=False)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    likes_count = serializers.SerializerMethodField()
    location_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    location = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Post
        fields = ['id', 'author', 'comments', 'text', 'created_at', 'location_name',
                  'likes_count', 'images', 'image', 'uploaded_images', 'location']
        

    def validate(self, data):
        """
        Валидация наличия хотя бы одного изображения при создании поста
        """
        request = self.context.get('request')
        
        # Проверяем, есть ли изображения в запросе
        has_images = (
            data.get('uploaded_images') or 
            data.get('image') or 
            (request and request.FILES.getlist('images'))
        )
        if self.instance is None and not has_images:
            raise ValidationError("К посту должно быть прикреплено хотя бы одно изображение")
        return data

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_location(self, obj):
        if obj.latitude and obj.longitude:
            location_data = {
                'latitude': float(obj.latitude),
                'longitude': float(obj.longitude),
            }
            if obj.location_name:
                location_data['name'] = obj.location_name
            return location_data
        return None

    def create(self, validated_data):
        request = self.context.get('request')

        # Проверяем наличие изображений перед созданием поста
        if not (validated_data.get('uploaded_images') or 
                validated_data.get('image') or 
                (request and request.FILES.getlist('images'))):
            raise ValidationError("К посту должно быть прикреплено хотя бы одно изображение")

        location_name = validated_data.pop('location_name', None)
        if location_name:
            try:
                geolocator = Nominatim(user_agent="social_network")
                location = geolocator.geocode(location_name)
                if location:
                    validated_data['latitude'] = location.latitude
                    validated_data['longitude'] = location.longitude
                    validated_data['location_name'] = location_name
            except GeocoderUnavailable:
                pass

        uploaded_images = validated_data.pop('uploaded_images', [])

        post = Post.objects.create(**validated_data)

        for img in uploaded_images:
            PostImage.objects.create(post=post, image=img)

        image = validated_data.get('image')
        if image:
            PostImage.objects.create(post=post, image=image)

        return post


