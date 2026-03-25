import json
import re

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import IntegrityError
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

from .models import BlogPost
from .services.youtube import get_title
from .services.transcription import get_transcription
from .services.ai_generation import generate_blog_from_transcription

# Regex pour valider les URLs YouTube
YOUTUBE_URL_PATTERN = re.compile(
    r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|embed/|v/)|youtu\.be/)[a-zA-Z0-9_-]{11}'
)


@login_required
def index(request):
    return render(request, 'index.html')


@login_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent.'}, status=400)

        # Validation de l'URL YouTube
        if not yt_link or not YOUTUBE_URL_PATTERN.match(yt_link):
            return JsonResponse({'error': 'Invalid YouTube URL.'}, status=400)

        existing = BlogPost.objects.filter(user=request.user, youtube_link=yt_link).first()
        if existing:
            return JsonResponse({
                'error': 'duplicate',
                'message': 'You already have an article for this video.',
                'article_id': existing.id
            }, status=400)

        title = get_title(yt_link)

        transcription = get_transcription(yt_link)
        if not transcription:
            return JsonResponse({
                'error': "Impossible de récupérer la transcription. "
                         "La vidéo n'a peut-être pas de sous-titres disponibles."
            }, status=500)

        blog_content = generate_blog_from_transcription(transcription)
        if not blog_content:
            return JsonResponse({'error': "Failed to generate the blog article"}, status=500)

        BlogPost.objects.create(
            user=request.user,
            youtube_title=title,
            youtube_link=yt_link,
            generated_content=blog_content,
        )

        return JsonResponse({'content': blog_content})
    else:
        return JsonResponse({'error': 'Invalid Request method.'}, status=405)


@login_required
def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})


@login_required
def blog_details(request, pk):
    blog_article_detail = get_object_or_404(BlogPost, id=pk, user=request.user)
    return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})


@login_required
def delete_blog(request, pk):
    if request.method == 'POST':
        article = get_object_or_404(BlogPost, id=pk, user=request.user)
        article.delete()
        messages.success(request, 'Article supprimé avec succès.')
    return redirect('blog-list')


@ratelimit(key='ip', rate='5/5m', method='POST', block=True)
def user_login(request):
    next_url = request.GET.get('next', '/')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '/')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenue, {username} ! Vous êtes connecté.')
            return redirect(next_url)
        else:
            return render(request, 'login.html', {
                'error_message': 'Identifiant ou mot de passe incorrect.',
                'next': next_url
            })

    return render(request, 'login.html', {'next': next_url})


@ratelimit(key='ip', rate='3/h', method='POST', block=True)
def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'signup.html', {'error_message': 'Les mots de passe ne correspondent pas.'})

        # Vérifier si l'utilisateur existe déjà
        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error_message': 'Ce nom d\'utilisateur est déjà pris.'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error_message': 'Cet email est déjà utilisé.'})

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f'Compte créé avec succès ! Bienvenue, {username} !')
            return redirect('/')
        except IntegrityError:
            return render(request, 'signup.html', {'error_message': 'Erreur lors de la création du compte. Veuillez réessayer.'})

    return render(request, 'signup.html')


def user_logout(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('/')

