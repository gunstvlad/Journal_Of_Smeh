# blog/nanobanana_api.py
from openai import OpenAI
from django.conf import settings
import requests
import base64
import re
import time
import logging

logger = logging.getLogger(__name__)


class NanoBananaAPI:
    def __init__(self):
        print(f"\n🔑 NanoBanana Init:")
        print(f"   Model: {settings.NANOBANANA_MODEL}")
        print(f"   Base URL: {settings.NANOBANANA_BASE_URL}")
        print(
            f"   Key: {settings.NANOBANANA_API_KEY[:15] if settings.NANOBANANA_API_KEY else 'EMPTY'}..."
        )

        self.client = OpenAI(
            base_url=settings.NANOBANANA_BASE_URL,
            api_key=settings.NANOBANANA_API_KEY,
        )
        self.model = settings.NANOBANANA_MODEL

    def generate_image(self, prompt, **kwargs):
        """Генерация с тремя стратегиями"""

        # 🔹 СТРАТЕГИЯ 1: Оригинальный промпт
        strategies = [
            {
                "name": "Original prompt",
                "prompt": prompt,
                "modalities": ["image", "text"],
            },
            # 🔹 СТРАТЕГИЯ 2: Упрощённый промпт на английском
            {
                "name": "Simple English",
                "prompt": self._simplify_prompt(prompt),
                "modalities": ["image", "text"],
            },
            # 🔹 СТРАТЕГИЯ 3: Без modalities (иногда помогает)
            {
                "name": "No modalities",
                "prompt": self._simplify_prompt(prompt),
                "modalities": None,
            },
        ]

        last_error = None

        for i, strategy in enumerate(strategies, 1):
            try:
                print(f"\n{'='*70}")
                print(f"🎯 STRATEGY {i}: {strategy['name']}")
                print(f"📝 Prompt: {strategy['prompt'][:100]}...")
                print(f"{'='*70}")

                # Формируем запрос
                request_params = {
                    "model": self.model,
                    "messages": [{"role": "user", "content": strategy["prompt"]}],
                    "timeout": 120,
                }

                # Добавляем modalities только если указаны
                if strategy["modalities"]:
                    request_params["extra_body"] = {
                        "modalities": strategy["modalities"]
                    }
                    print(f"📡 Modalities: {strategy['modalities']}")
                else:
                    print(f"📡 Modalities: NONE")

                # Отправляем запрос
                print(f"⏳ Sending request...")
                response = self.client.chat.completions.create(**request_params)

                # Логируем ответ
                self._log_response(response)

                # Пробуем извлечь изображение
                if hasattr(response, "choices") and response.choices:
                    message = response.choices[0].message

                    # Проверяем images
                    if hasattr(message, "images") and message.images:
                        print(f"✅ SUCCESS! Found {len(message.images)} image(s)")
                        image_url = self._extract_url_from_image(message.images[0])
                        if image_url:
                            return {
                                "image_url": image_url,
                                "revised_prompt": strategy["prompt"],
                            }

                    # Проверяем content на наличие URL
                    if hasattr(message, "content") and message.content:
                        urls = re.findall(
                            r'https?://[^\s<>"\']+\.(?:png|jpg|jpeg|webp|gif)',
                            message.content,
                        )
                        if urls:
                            print(f"🔗 Found URL in text content")
                            return {
                                "image_url": urls[0],
                                "revised_prompt": strategy["prompt"],
                            }

                print(f"❌ Strategy {i} failed: No images found")
                last_error = Exception(f"Strategy {i} failed")

            except Exception as e:
                print(f"❌ Strategy {i} error: {e}")
                last_error = e
                time.sleep(2)  # Пауза перед следующей попыткой
                continue

        # Все стратегии провалились
        raise Exception(f"All strategies failed. Last error: {last_error}")

    def _simplify_prompt(self, prompt):
        """Упрощает промпт для лучшей совместимости"""
        # Убираем русские слова, которые могут сбить с толку
        simplifications = {
            "мем": "image",
            "смешной": "funny",
            "создай": "generate",
            "добавь текст": "",
            "сверху": "",
            "снизу": "",
            "интернет-мем": "digital art",
            "юмористично": "humorous style",
        }

        result = prompt
        for ru, en in simplifications.items():
            result = result.replace(ru, en)

        # Добавляем магические слова для генерации
        if "image" not in result.lower() and "generate" not in result.lower():
            result = f"Generate a high-quality image: {result}"

        # Убеждаемся, что есть стиль
        if "style" not in result.lower():
            result += ", high quality, detailed, vibrant colors"

        return result.strip()

    def _log_response(self, response):
        """Детальное логирование ответа"""
        print(f"\n📥 Response received:")
        print(f"   Model: {response.model}")
        print(f"   Choices: {len(response.choices)}")

        if response.choices:
            message = response.choices[0].message
            print(f"   Message type: {type(message).__name__}")
            print(f"   Has 'images' attr: {hasattr(message, 'images')}")

            if hasattr(message, "images"):
                print(f"   Images: {message.images}")
                if message.images:
                    print(f"   First image type: {type(message.images[0])}")
                    if isinstance(message.images[0], dict):
                        print(f"   Dict keys: {list(message.images[0].keys())}")

            if hasattr(message, "content") and message.content:
                content_preview = message.content[:150].replace("\n", " ")
                print(f"   Content: {content_preview}...")

            # Выводим все атрибуты для отладки
            attrs = [
                a
                for a in dir(message)
                if not a.startswith("_") and not callable(getattr(message, a))
            ]
            print(f"   All attrs: {attrs[:10]}")

    def _extract_url_from_image(self, image):
        """Извлечение URL"""
        if isinstance(image, dict):
            if image.get("url"):
                return image["url"]
            if image.get("image_url"):
                iu = image["image_url"]
                if isinstance(iu, dict):
                    return iu.get("url")
                elif isinstance(iu, str):
                    return iu
            if image.get("data"):
                return image["data"]
            return None

        if hasattr(image, "url") and image.url:
            return image.url
        if hasattr(image, "image_url"):
            iu = image.image_url
            if isinstance(iu, str):
                return iu
            elif hasattr(iu, "url"):
                return iu.url
        if hasattr(image, "data") and image.data:
            return image.data

        return None

    def download_image(self, image_url):
        """Скачивание изображения"""
        if image_url.startswith("http"):
            print(f"📥 Downloading from HTTP...")
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return response.content
        elif "base64" in image_url or image_url.startswith("image"):
            print(f"📥 Decoding base64...")
            try:
                return base64.b64decode(image_url.split(",", 1)[1])
            except:
                return base64.b64decode(image_url)
        else:
            try:
                return base64.b64decode(image_url)
            except:
                raise Exception(f"Unknown format: {image_url[:50]}...")
