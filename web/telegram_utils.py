"""Утилиты для работы с Telegram Bot API"""

import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


async def get_user_profile_photo_url(bot_token: str, user_id: int) -> Optional[str]:
    """Получает URL фото профиля пользователя из Telegram

    Args:
        bot_token: Токен Telegram бота
        user_id: ID пользователя в Telegram

    Returns:
        URL фото профиля или None если фото не найдено
    """
    try:
        async with httpx.AsyncClient() as client:
            # Получаем список фотографий профиля
            response = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getUserProfilePhotos",
                params={"user_id": user_id, "limit": 1}
            )

            if response.status_code != 200:
                logger.warning(f"Не удалось получить фото профиля для user_id={user_id}: {response.status_code}")
                return None

            data = response.json()

            if not data.get("ok") or not data.get("result", {}).get("photos"):
                logger.debug(f"У пользователя {user_id} нет фото профиля")
                return None

            # Берем первое фото (самое большое разрешение - последний элемент в массиве размеров)
            photo_sizes = data["result"]["photos"][0]
            if not photo_sizes:
                return None

            # Берем самый большой размер
            largest_photo = photo_sizes[-1]
            file_id = largest_photo["file_id"]

            # Получаем путь к файлу
            file_response = await client.get(
                f"https://api.telegram.org/bot{bot_token}/getFile",
                params={"file_id": file_id}
            )

            if file_response.status_code != 200:
                logger.warning(f"Не удалось получить путь к файлу для file_id={file_id}")
                return None

            file_data = file_response.json()

            if not file_data.get("ok"):
                return None

            file_path = file_data["result"]["file_path"]

            # Формируем URL для скачивания
            photo_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

            return photo_url

    except Exception as e:
        logger.error(f"Ошибка при получении фото профиля для user_id={user_id}: {e}")
        return None


def get_fallback_avatar_url(display_name: str) -> str:
    """Получает fallback URL аватара через ui-avatars.com

    Args:
        display_name: Имя пользователя

    Returns:
        URL аватара
    """
    return f"https://ui-avatars.com/api/?name={display_name}&background=random"
