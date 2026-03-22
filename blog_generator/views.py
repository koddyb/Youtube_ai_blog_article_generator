import json

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages

from .models import BlogPost
from .services.youtube import get_title
from .services.transcription import get_transcription
from .services.ai_generation import generate_blog_from_transcription


@login_required
def index(request):
    return render(request, 'index.html')


@csrf_exempt
def generate_blog(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            yt_link = data['link']
        except (KeyError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid data sent.'}, status=400)

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


def blog_list(request):
    blog_articles = BlogPost.objects.filter(user=request.user).order_by('-created_at')
    
    return render(request, "all-blogs.html", {'blog_articles': blog_articles})


def blog_details(request, pk):
    blog_article_detail = BlogPost.objects.get(id=pk)
    if request.user != blog_article_detail.user:
        return redirect('/')
    return render(request, 'blog-details.html', {'blog_article_detail': blog_article_detail})


def delete_blog(request, pk):
    if request.method == 'POST':
        article = BlogPost.objects.get(id=pk)
        if request.user == article.user:
            article.delete()
            messages.success(request, 'Article supprimé avec succès.')
    return redirect('blog-list')


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Bienvenue, {username} ! Vous êtes connecté.')
            return redirect('/')
        else:
            return render(request, 'login.html', {'error_message': 'Identifiant ou mot de passe incorrect.'})

    return render(request, 'login.html')


def user_signup(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            return render(request, 'signup.html', {'error_message': 'Les mots de passe ne correspondent pas.'})

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            login(request, user)
            messages.success(request, f'Compte créé avec succès ! Bienvenue, {username} !')
            return redirect('/')
        except Exception as e:
            return render(request, 'signup.html', {'error_message': str(e)})

    return render(request, 'signup.html')


def user_logout(request):
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('/')

