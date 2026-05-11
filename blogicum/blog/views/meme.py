# blog/views/memes.py
import uuid
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.base import ContentFile
from django.utils import timezone

from blog.models import Post
from blog.nanobanana_api import NanoBananaAPI

from django.conf import settings


@login_required
def generate_meme(request):
    """Генератор мемов через NanoBanana (Gemini 3 Pro)"""
    print("\n" + "=" * 70)
    print("🔍 DJANGO SETTINGS DEBUG:")
    print(
        f"  - NANOBANANA_API_KEY: {settings.NANOBANANA_API_KEY[:20] if settings.NANOBANANA_API_KEY else 'EMPTY'}..."
    )
    print(f"  - NANOBANANA_BASE_URL: {settings.NANOBANANA_BASE_URL}")
    print(f"  - NANOBANANA_MODEL: {settings.NANOBANANA_MODEL}")
    print(f"  - .env loaded: {bool(settings.NANOBANANA_API_KEY)}")
    print("=" * 70 + "\n")
    if request.method == "POST":
        joke_description = request.POST.get("joke_description", "").strip()
        text_top = request.POST.get("text_top", "").strip()
        text_bottom = request.POST.get("text_bottom", "").strip()

        # Валидация
        if not joke_description:
            messages.error(request, "Опиши свою шутку или идею мема!")
            return render(
                request,
                "blog/meme_generator.html",
                {
                    "joke_description": joke_description,
                    "text_top": text_top,
                    "text_bottom": text_bottom,
                },
            )

        try:
            api = NanoBananaAPI()
            prompt = f"Создай смешной мем по описанию: {joke_description}"

            if text_top or text_bottom:
                prompt += f". Добавь текст: сверху '{text_top}', снизу '{text_bottom}'"

            prompt += ". Стиль: интернет-мем, ярко, юмористично, высокое качество"

            result = api.generate_image(prompt=prompt)
            image_data = api.download_image(result["image_url"])
            filename = f"meme_{request.user.id}_{uuid.uuid4().hex[:8]}.png"

            # 🔹 НОВОЕ: Кодируем в base64 для шаблона
            import base64

            image_base64 = base64.b64encode(image_data).decode("utf-8")

            messages.success(request, "Мем сгенерирован!")
            return render(
                request,
                "blog/meme_result.html",
                {
                    "image_base64": image_base64,  # ← Base64 строка
                    "image_data": image_data,  # ← Бинарные данные (для формы)
                    "filename": filename,
                    "joke_description": joke_description,
                    "text_top": text_top,
                    "text_bottom": text_bottom,
                    "revised_prompt": result.get("revised_prompt", prompt),
                },
            )

        except Exception as e:
            error_msg = str(e)
            if "API key" in error_msg or "authentication" in error_msg.lower():
                messages.error(request, "Ошибка ключа API. Проверь настройки.")
            elif "timeout" in error_msg.lower():
                messages.error(request, "Превышено время ожидания. Попробуй ещё раз.")
            elif "quota" in error_msg.lower() or "limit" in error_msg.lower():
                messages.error(request, "Превышен лимит запросов. Проверь баланс.")
            else:
                messages.error(request, f"Ошибка генерации: {error_msg}")

            return render(
                request,
                "blog/meme_generator.html",
                {
                    "joke_description": joke_description,
                    "text_top": text_top,
                    "text_bottom": text_bottom,
                },
            )

    return render(request, "blog/meme_generator.html")


@login_required
def save_meme_as_post(request):
    if request.method != "POST":
        return redirect("blog:generate_meme")

    try:
        image_data = request.POST.get("image_data")
        filename = request.POST.get("filename")
        joke_description = request.POST.get("joke_description", "AI Мем")
        text_top = request.POST.get("text_top", "")
        text_bottom = request.POST.get("text_bottom", "")
        revised_prompt = request.POST.get("revised_prompt", "")

        if not image_data:
            messages.error(request, "Нет изображения для сохранения")
            return redirect("blog:generate_meme")

        # Декодируем base64
        from base64 import b64decode

        image_file = ContentFile(b64decode(image_data), name=filename)

        # Создаём пост
        title = joke_description[:50]
        text = f"Сгенерировано по шутке: {joke_description}"
        if text_top or text_bottom:
            text += f'\n\nТекст на меме: "{text_top}" / "{text_bottom}"'
        if revised_prompt:
            text += f"\n\nAI промпт: {revised_prompt}"

        post = Post(
            title=title,
            text=text,
            author=request.user,
            is_published=True,
            pub_date=timezone.now(),
        )
        post.image.save(filename, image_file, save=True)

        messages.success(request, "Мем опубликован в блоге!")
        return redirect("blog:post_detail", post_id=post.id)

    except Exception as e:
        messages.error(request, f"Ошибка сохранения: {str(e)}")
        return redirect("blog:generate_meme")


@login_required
def meme_gallery(request):
    memes = (
        Post.objects.filter(text__icontains="Сгенерировано по шутке")
        .select_related("author")
        .order_by("-created_at")
    )

    return render(request, "blog/meme_gallery.html", {"memes": memes})
