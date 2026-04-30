# blog/nanobanana_api.py
from openai import OpenAI
from django.conf import settings
import requests
import base64
import re


class NanoBananaAPI:
    """
    Клиент для работы с NanoBanana (Gemini 3 Pro Image Preview)
    Через прокси: https://api.zveno.ai/v1
    """
    
    def __init__(self):
        self.client = OpenAI(
            base_url=settings.NANOBANANA_BASE_URL,
            api_key=settings.NANOBANANA_API_KEY,
        )
        self.model = settings.NANOBANANA_MODEL
    
    def generate_image(self, prompt, aspect_ratio=None, **kwargs):
        """
        Генерация изображения через Gemini 3 Pro Image Preview
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                extra_body={"modalities": ["image", "text"]},
                timeout=120
            )
            
            message = response.choices[0].message
            
            # Проверка на наличие изображений
            if not (hasattr(message, 'images') and message.images):
                # Запасной вариант: ищем ссылку в тексте ответа
                content = getattr(message, 'content', '')
                urls = re.findall(r'https?://[^\s<>"\']+\.(?:png|jpg|jpeg|webp|gif)', content)
                if urls:
                    return {'image_url': urls[0], 'revised_prompt': prompt}
                raise Exception('No images in response')
            
            # Извлекаем URL из первого изображения
            image = message.images[0]
            image_url = self._extract_url_from_image(image)
            
            if not image_url:
                raise Exception('Could not extract image URL from response')
            
            return {
                'image_url': image_url,
                'revised_prompt': getattr(message, 'content', prompt),
            }
            
        except Exception as e:
            if hasattr(e, 'body'):
                raise Exception(f'NanoBanana API error: {e.body}')
            raise Exception(f'NanoBanana API error: {str(e)}')
    
    def _extract_url_from_image(self, image):
        """
        Извлекает URL изображения из dict или объекта
        """
        # Если это словарь (dict)
        if isinstance(image, dict):
            if image.get('url'):
                return image['url']
            if image.get('image_url'):
                iu = image['image_url']
                if isinstance(iu, dict):
                    return iu.get('url')
                elif isinstance(iu, str):
                    return iu
            if image.get('data'):
                return image['data']
            return None
        
        # Если это объект с атрибутами
        if hasattr(image, 'url') and image.url:
            return image.url
        if hasattr(image, 'image_url'):
            iu = image.image_url
            if isinstance(iu, str):
                return iu
            elif hasattr(iu, 'url'):
                return iu.url
        if hasattr(image, 'data') and image.data:
            return image.data
        
        return None
    
    def download_image(self, image_url):
        """
        Скачивает изображение по URL или декодирует base64
        """
        if image_url.startswith('http'):
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return response.content
        elif image_url.startswith('image'):
            # image/png;base64,ABCD...
            header, encoded = image_url.split(',', 1)
            return base64.b64decode(encoded)
        else:
            # Пробуем как base64 на всякий случай
            try:
                return base64.b64decode(image_url)
            except Exception:
                raise Exception(f'Unknown image URL format: {image_url[:50]}...')
    
    def check_balance(self):
        """Проверка баланса (если API поддерживает)"""
        return None