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


async def send_telegram_message(
    bot_token: str,
    chat_id: int,
    text: str,
    reply_markup: dict = None
) -> Optional[int]:
    """Отправляет сообщение в Telegram чат

    Args:
        bot_token: Токен Telegram бота
        chat_id: ID чата для отправки
        text: Текст сообщения (HTML)
        reply_markup: Опциональная клавиатура (InlineKeyboardMarkup в формате dict)

    Returns:
        message_id отправленного сообщения или None в случае ошибки
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }

            if reply_markup:
                import json
                data['reply_markup'] = json.dumps(reply_markup)

            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                data=data
            )

            if response.status_code != 200:
                logger.error(f"Ошибка при отправке сообщения в Telegram: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API вернул ошибку: {result.get('description')}")
                return None

            message_id = result.get("result", {}).get("message_id")
            logger.info(f"Сообщение успешно отправлено в чат {chat_id}, message_id: {message_id}")
            return message_id

    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения в Telegram: {e}")
        return None


async def send_telegram_document(
    bot_token: str,
    chat_id: int,
    document_file_id: str,
    caption: str = None
) -> Optional[int]:
    """Отправляет документ по file_id в Telegram чат

    Args:
        bot_token: Токен Telegram бота
        chat_id: ID чата для отправки
        document_file_id: file_id документа в Telegram
        caption: Опциональная подпись к документу

    Returns:
        message_id отправленного сообщения или None в случае ошибки
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            data = {
                'chat_id': chat_id,
                'document': document_file_id
            }

            if caption:
                data['caption'] = caption

            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendDocument",
                data=data
            )

            if response.status_code != 200:
                logger.error(f"Ошибка при отправке документа в Telegram: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API вернул ошибку: {result.get('description')}")
                return None

            message_id = result.get("result", {}).get("message_id")
            logger.info(f"Документ успешно отправлен в чат {chat_id}, message_id: {message_id}")
            return message_id

    except Exception as e:
        logger.error(f"Ошибка при отправке документа в Telegram: {e}")
        return None


async def upload_file_to_storage(
    bot_token: str,
    storage_chat_id: int,
    file_bytes: bytes,
    filename: str
) -> Optional[str]:
    """Загружает файл в служебный чат Telegram и возвращает file_id

    Args:
        bot_token: Токен Telegram бота
        storage_chat_id: ID приватной группы для хранения файлов
        file_bytes: Байты файла
        filename: Имя файла

    Returns:
        file_id от Telegram или None в случае ошибки
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Формируем multipart/form-data для отправки файла
            files = {
                'document': (filename, file_bytes)
            }
            data = {
                'chat_id': storage_chat_id
            }

            # Отправляем файл в служебный чат
            response = await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendDocument",
                files=files,
                data=data
            )

            if response.status_code != 200:
                logger.error(f"Ошибка при загрузке файла в Telegram: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            result = response.json()

            if not result.get("ok"):
                logger.error(f"Telegram API вернул ошибку: {result.get('description')}")
                return None

            # Извлекаем file_id из ответа
            file_id = result.get("result", {}).get("document", {}).get("file_id")

            if not file_id:
                logger.error(f"file_id не найден в ответе Telegram API")
                return None

            logger.info(f"Файл {filename} успешно загружен в storage_chat, file_id: {file_id}")
            return file_id

    except Exception as e:
        logger.error(f"Ошибка при загрузке файла {filename} в Telegram: {e}")
        return None
