"""Базовый клиент для работы с Yandex Tracker API."""

import os
from typing import Optional
from dotenv import load_dotenv
from YaTrackerApi import YandexTrackerClient

class TrackerClient:
    """Обертка над YandexTrackerClient с загрузкой из .env."""

    def __init__(
        self,
        oauth_token: Optional[str] = None,
        org_id: Optional[str] = None,
        log_level: str = "WARNING"
    ):
        """
        Инициализация клиента Tracker.

        Args:
            oauth_token: OAuth токен (если None - загружается из .env)
            org_id: ID организации (если None - загружается из .env)
            log_level: Уровень логирования (WARNING - не показывать детальные INFO логи API)
        """
        load_dotenv()

        self.oauth_token = oauth_token or os.getenv("TRACKER_API_KEY")
        self.org_id = org_id or os.getenv("TRACKER_ORG_ID")
        self.log_level = log_level

        if not self.oauth_token:
            raise ValueError("TRACKER_API_KEY не найден в .env файле")
        if not self.org_id:
            raise ValueError("TRACKER_ORG_ID не найден в .env файле")

        self._client: Optional[YandexTrackerClient] = None

    async def __aenter__(self):
        """Асинхронный вход в контекстный менеджер."""
        self._client = YandexTrackerClient(
            oauth_token=self.oauth_token,
            org_id=self.org_id,
            log_level=self.log_level
        )
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный выход из контекстного менеджера."""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    @property
    def client(self) -> YandexTrackerClient:
        """Получение экземпляра YandexTrackerClient."""
        if not self._client:
            raise RuntimeError("Клиент не инициализирован. Используйте 'async with'")
        return self._client
