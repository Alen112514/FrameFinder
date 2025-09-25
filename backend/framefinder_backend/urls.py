"""
URL configuration for framefinder_backend project.

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
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from api.views import VideoViewSet, clip, video_status_stream

router = DefaultRouter()
router.register(r'videos', VideoViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/clip/', clip, name='clip-with-slash'),
    path('api/clip', clip, name='clip-no-slash'),
    path('api/videos/<uuid:video_id>/status-stream/', video_status_stream, name='video-status-stream'),
    # Add explicit patterns for URLs without trailing slash
    path('api/videos', include([
        path('', VideoViewSet.as_view({'get': 'list', 'post': 'create'}), name='video-list-no-slash'),
        path('/<uuid:pk>', VideoViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='video-detail-no-slash'),
        path('/<uuid:pk>/search', VideoViewSet.as_view({'post': 'search'}), name='video-search-no-slash'),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
