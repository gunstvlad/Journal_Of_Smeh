# blog/views/memes.py
import uuid
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile

from blog.models import Post
from blog.nanobanana_api import NanoBananaAPI


@login_required
def generate_meme(request):
    if request.method == 'POST':
        joke_description = request.POST.get('joke_description', '').strip()
        text_top = request.POST.get('text_top', '').strip()
        text_bottom = request.POST.get('text_bottom', '').strip()
        aspect_ratio = request.POST.get('aspect_ratio', '1:1')
        save_as_post = request.POST.get('save_as_post')
        
        if not joke_description:
            messages.error(request, 'Опиши свою шутку или идею мема!')
            return render(request, 'blog/meme_generator.html', {
                'joke_description': joke_description,
                'text_top': text_top,
                'text_bottom': text_bottom,
            })
        
        try:
            api = NanoBananaAPI()
            prompt = f"Создай смешной мем по описанию: {joke_description}"
            
            if text_top or text_bottom:
                prompt += f". Добавь текст: сверху '{text_top}', снизу '{text_bottom}'"

            prompt += ". Стиль: интернет-мем, ярко, юмористично, высокое качество"
            result = api.generate_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio
            )
            
            image_data = api.download_image(result['image_url'])
            filename = f'meme_{request.user.id}_{uuid.uuid4().hex[:8]}.png'
            
            if save_as_post:
                post = Post(
                    title=f'{joke_description[:50]}',
                    text=f'Сгенерировано по шутке: {joke_description}\n\n промпт: {result["revised_prompt"]}',
                    author=request.user,
                    is_published=True,
                )
                post.image.save(filename, ContentFile(image_data), save=True)
                messages.success(request, 'Мем сгенерирован и опубликован!')
                return redirect('blog:post_detail', post_id=post.id)
            else:
                messages.success(request, 'Мем сгенерирован!')
                return render(request, 'blog/meme_result.html', {
                    'image_url': result['image_url'],
                    'image_data': image_data,
                    'joke_description': joke_description,
                    'revised_prompt': result['revised_prompt'],
                })
        
        except Exception as e:
            error_msg = str(e)
            if 'API key' in error_msg or 'authentication' in error_msg.lower():
                messages.error(request, 'Ошибка ключа API. Проверь настройки.')
            elif 'timeout' in error_msg.lower():
                messages.error(request, 'Превышено время ожидания. Попробуй ещё раз.')
            elif 'quota' in error_msg.lower() or 'limit' in error_msg.lower():
                messages.error(request, 'Превышен лимит запросов. Проверь баланс.')
            else:
                messages.error(request, f'Ошибка генерации: {error_msg}')
            
            return render(request, 'blog/meme_generator.html', {
                'joke_description': joke_description,
                'text_top': text_top,
                'text_bottom': text_bottom,
            })
    
    return render(request, 'blog/meme_generator.html')


@login_required
def meme_gallery(request):
    memes = Post.objects.filter(
        text__icontains='Сгенерировано по шутке'
    ).select_related('author').order_by('-created_at')
    
    return render(request, 'blog/meme_gallery.html', {'memes': memes})