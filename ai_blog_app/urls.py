"""
URL configuration for ai_blog_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.shortcuts import render

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('blog_generator.urls')),
]

urlpatterns = urlpatterns+static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Custom error handlers
def custom_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def custom_403(request, exception):
    return render(request, 'errors/403.html', {'exception': str(exception)}, status=403)

def custom_500(request):
    return render(request, 'errors/500.html', status=500)

handler404 = custom_404
handler403 = custom_403
handler500 = custom_500
