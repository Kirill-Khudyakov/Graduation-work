"""
URL configuration for network project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static

from ShotLine.views import CommentDetail, CommentList, LikeDetail, LikeList, PostDetail, PostImageDetail, PostImageList, PostList, start


urlpatterns = [
    path('', start),
    path('admin/', admin.site.urls),

    # Посты
    path('api/posts/', PostList.as_view(), name='post-list'),
    path('api/posts/<int:pk>/', PostDetail.as_view(), name='post-detail'),

    # Изображения постов
    path('api/posts/<int:post_id>/images/', PostImageList.as_view(), name='post-image-list'),
    path('api/posts/<int:post_id>/images/<int:pk>/', PostImageDetail.as_view(), name='post-image-detail'),

    # Лайки
    path('api/posts/<int:post_id>/likes/', LikeList.as_view(), name='post-like-list'),
    path('api/posts/<int:post_id>/likes/<int:pk>/', LikeDetail.as_view(), name='post-like-detail'),

    # Комментарии
    path('api/posts/<int:post_id>/comments/', CommentList.as_view(), name='post-comment-list'),
    path('api/posts/<int:post_id>/comments/<int:pk>/', CommentDetail.as_view(), name='post-comment-detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)