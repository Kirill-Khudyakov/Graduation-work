from rest_framework import generics, filters, permissions
from rest_framework.exceptions import ValidationError

from .permissions import IsAuthorOrReadOnly
from .serializers import CommentSerializer, LikeSerializer, PostImageSerializer, PostSerializer
from .models import Post, PostImage, Like, Comment
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Класс пагинации с настройками по умолчанию:
    - 10 объектов на страницу
    - параметр запроса 'page_size' для изменения размера страницы
    - максимальный размер страницы 100
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AuthorCheckMixin:
    """
    Миксин для проверки авторства объекта при обновлении и удалении.
    Позволяет разрешать операции только автору объекта.
    """

    def perform_update(self, serializer):
        """
        Проверяет, что текущий пользователь является автором объекта.
        Если нет — выбрасывает ValidationError.
        """
        author = getattr(serializer.instance, 'author', None) or getattr(serializer.instance, 'user', None)
        if author != self.request.user:
            raise ValidationError("Вы можете изменять только свои объекты")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        """
        Проверяет, что текущий пользователь является автором объекта.
        Если нет — выбрасывает ValidationError.
        """
        author = getattr(instance, 'author', None) or getattr(instance, 'user', None)
        if author != self.request.user:
            raise ValidationError("Вы можете удалять только свои объекты")
        super().perform_destroy(instance)


class PostList(generics.ListCreateAPIView):
    """
    Представление для вывода списка постов и создания нового поста.
    Поддерживает поиск по тексту, автору и местоположению, а также сортировку.
    """
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['text', 'author__username', 'location_name']
    ordering_fields = ['created_at', 'likes_count']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """
        При создании поста автоматически устанавливает автора в текущего пользователя.
        """
        serializer.save(author=self.request.user)


class PostDetail(AuthorCheckMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Представление для получения, обновления и удаления отдельного поста.
    Обновлять и удалять может только автор поста.
    """
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]


class PostImageList(generics.ListCreateAPIView):
    """
    Представление для списка изображений конкретного поста и добавления новых изображений.
    """
    serializer_class = PostImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Возвращает список изображений, связанных с постом из URL-параметра post_id.
        """
        post_id = self.kwargs.get('post_id')
        return PostImage.objects.filter(post_id=post_id)

    def perform_create(self, serializer):
        """
        При создании изображения привязывает его к посту из URL-параметра post_id.
        """
        post_id = self.kwargs.get('post_id')
        if not post_id:
            raise ValidationError("post_id is required in URL")
        serializer.save(post_id=post_id)


class PostImageDetail(AuthorCheckMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Представление для получения, обновления и удаления отдельного изображения поста.
    Изменять и удалять может только автор.
    """
    queryset = PostImage.objects.all()
    serializer_class = PostImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]


class LikeList(generics.ListCreateAPIView):
    """
    Представление для списка лайков конкретного поста и создания лайка.
    Пользователь может поставить лайк только один раз.
    """
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Возвращает лайки, связанные с постом из URL-параметра post_id.
        Если post_id не указан, возвращает все лайки.
        """
        post_id = self.kwargs.get('post_id')
        if post_id:
            return Like.objects.filter(post_id=post_id)
        return Like.objects.all()

    def perform_create(self, serializer):
        """
        При создании лайка проверяет, что пользователь ещё не лайкал этот пост.
        Если лайк уже есть — выбрасывает ValidationError.
        """
        post_id = self.kwargs.get('post_id')
        post = generics.get_object_or_404(Post, pk=post_id)

        if Like.objects.filter(post=post, user=self.request.user).exists():
            raise ValidationError("Вы уже поставили лайк этому посту")

        serializer.save(user=self.request.user, post=post)


class LikeDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Представление для получения, обновления и удаления отдельного лайка.
    Изменять и удалять лайк может только его создатель.
    """
    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        """
        Проверяет авторство лайка перед обновлением.
        """
        if serializer.instance.user != self.request.user:
            raise ValidationError("Вы можете изменять только свои лайки")
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        """
        Проверяет авторство лайка перед удалением.
        """
        if instance.user != self.request.user:
            raise ValidationError("Вы можете удалять только свои лайки")
        super().perform_destroy(instance)


class CommentList(generics.ListCreateAPIView):
    """
    Представление для списка комментариев к посту и создания нового комментария.
    """
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        """
        Возвращает комментарии, связанные с постом из URL-параметра post_id,
        отсортированные по дате создания (сначала новые).
        """
        post_id = self.kwargs.get('post_id')
        if post_id:
            return Comment.objects.filter(post_id=post_id).order_by('-created_at')
        return Comment.objects.all().order_by('-created_at')

    def perform_create(self, serializer):
        """
        При создании комментария устанавливает автора и связывает с постом из URL.
        """
        post_id = self.kwargs.get('post_id')
        post = generics.get_object_or_404(Post, pk=post_id)
        serializer.save(author=self.request.user, post=post)


class CommentDetail(AuthorCheckMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Представление для получения, обновления и удаления отдельного комментария.
    Изменять и удалять комментарий может только его автор.
    """
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
