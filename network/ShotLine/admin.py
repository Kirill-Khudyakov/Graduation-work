from django.contrib import admin

from django.utils.html import format_html
from .models import Post, PostImage, Like, Comment
from django.contrib import messages


class CommentInline(admin.TabularInline):
    model = Comment
    fields = ('author_link', 'text', 'created_at')
    readonly_fields = ('author_link', 'text', 'created_at')
    extra = 0
    can_delete = True
    show_change_link = True

    def author_link(self, obj):
        if obj.author:
            url = f'/admin/auth/user/{obj.author.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.author.username)
        return '-'
    author_link.short_description = 'Автор'


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author_username', 'text_preview', 'created_at', 'location_info', 'likes_count_display')
    list_filter = ('created_at', 'author')
    search_fields = ('text', 'author__username', 'location_name')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'likes_count_display', 'image_preview')
    fieldsets = (
        (None, {
            'fields': ('author', 'text',)
        }),
        ('Локация', {
            'fields': ('location_name', 'latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('likes_count_display', 'image_preview'),
            'classes': ('collapse',)
        }),
    )
    inlines = [CommentInline]

    def author_username(self, obj):
        return obj.author.username
    author_username.short_description = 'Автор'
    author_username.admin_order_field = 'author__username'

    def text_preview(self, obj):
        return obj.text[:100] + ('...' if len(obj.text) > 100 else '')
    text_preview.short_description = 'Текст'

    def location_info(self, obj):
        if obj.latitude and obj.longitude:
            return f"{obj.location_name or 'Нет названия'} ({obj.latitude}, {obj.longitude})"
        return obj.location_name or '—'
    location_info.short_description = 'Локация'

    def likes_count_display(self, obj):
        return obj.likes_count
    likes_count_display.short_description = 'Лайков'

    def image_preview(self, obj):
        # Показываем первое изображение из связанных PostImage
        first_image = obj.images.first() if hasattr(obj, 'images') else None
        if first_image and first_image.image:
            return format_html('<img src="{}" height="150" />', first_image.image.url)
        return '—'
    image_preview.short_description = 'Превью изображения'

    # Ограничение редактирования постов — только авторы и суперюзеры
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(author=request.user)

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return True  # Для списка объектов
        return request.user.is_superuser or obj.author == request.user

    def has_delete_permission(self, request, obj=None):
        if obj is None:
            return True
        return request.user.is_superuser or obj.author == request.user
    
    actions = ['delete_selected_posts']
    
    def delete_selected_posts(self, request, queryset):
        # Каскадное удаление связанных объектов
        for post in queryset:
            # Удаляем все связанные объекты перед удалением поста
            post.images.all().delete()
            post.likes.all().delete()
            post.comments.all().delete()
            post.delete()
        
        count = queryset.count()
        self.message_user(request,f'Успешно удалено {count} публикаций и всех связанных данных', messages.SUCCESS)
    delete_selected_posts.short_description = "Удалить выбранные публикации (со всем содержимым)"

    def delete_model(self, request, obj):
        # Удаление одной публикации
        obj.images.all().delete()
        obj.likes.all().delete()
        obj.comments.all().delete()
        obj.delete()
        self.message_user(request,'Публикация и все связанные данные успешно удалены',messages.SUCCESS)


@admin.register(PostImage)
class PostImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'post_link', 'image_preview', 'created_at')
    list_filter = ('post__author', 'created_at')
    search_fields = ('post__text', 'post__author__username')
    readonly_fields = ('image_preview_large',)
    date_hierarchy = 'created_at'

    def post_link(self, obj):
        url = f'/admin/ShotLine/post/{obj.post.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.post)
    post_link.short_description = 'Пост'
    post_link.admin_order_field = 'post'

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="50" />', obj.image.url)
        return '—'
    image_preview.short_description = 'Превью'

    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" height="300" />', obj.image.url)
        return '—'
    image_preview_large.short_description = 'Изображение'

    actions = ['delete_selected_images']
    
    def delete_selected_images(self, request, queryset):
        queryset.delete()
        self.message_user(request,f'Успешно удалено {queryset.count()} изображений',messages.SUCCESS)
    delete_selected_images.short_description = "Удалить выбранные изображения"


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'post_link', 'created_at')
    list_filter = ('user', 'post__author', 'created_at')
    search_fields = ('user__username', 'post__text')
    date_hierarchy = 'created_at'
    raw_id_fields = ('user', 'post')

    def user_link(self, obj):
        url = f'/admin/auth/user/{obj.user.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user'

    def post_link(self, obj):
        url = f'/admin/ShotLine/post/{obj.post.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.post)
    post_link.short_description = 'Пост'
    post_link.admin_order_field = 'post'

    actions = ['delete_selected_likes']
    
    def delete_selected_likes(self, request, queryset):
        queryset.delete()
        self.message_user(request,f'Успешно удалено {queryset.count()} лайков',messages.SUCCESS)
    delete_selected_likes.short_description = "Удалить выбранные лайки"


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author_link', 'post_link', 'text_preview', 'created_at')
    list_filter = ('author', 'post__author', 'created_at')
    search_fields = ('text', 'author__username', 'post__text')
    date_hierarchy = 'created_at'
    raw_id_fields = ('author', 'post')

    def author_link(self, obj):
        url = f'/admin/auth/user/{obj.author.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.author.username)
    author_link.short_description = 'Автор'
    author_link.admin_order_field = 'author'

    def post_link(self, obj):
        url = f'/admin/ShotLine/post/{obj.post.id}/change/'
        return format_html('<a href="{}">{}</a>', url, obj.post)
    post_link.short_description = 'Пост'
    post_link.admin_order_field = 'post'

    def text_preview(self, obj):
        return obj.text[:100] + ('...' if len(obj.text) > 100 else '')
    text_preview.short_description = 'Текст'

    actions = ['delete_selected_comments']
    
    def delete_selected_comments(self, request, queryset):
        queryset.delete()
        self.message_user(request,f'Успешно удалено {queryset.count()} комментариев',messages.SUCCESS)
    delete_selected_comments.short_description = "Удалить выбранные комментарии"

    def delete_model(self, request, obj):
        obj.delete()
        self.message_user(request,'Комментарий успешно удален',messages.SUCCESS)