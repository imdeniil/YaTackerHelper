"""Модальные окна"""

from typing import List
from fasthtml.common import *


def analytics_modal(stats_items: List) -> Div:
    """Модальное окно с аналитикой"""
    return Div(
        # Модальное окно
        Dialog(
            Div(
                # Заголовок
                Div(
                    H3("📊 Аналитика", cls="font-bold text-lg"),
                    Button(
                        "✕",
                        type="button",
                        cls="btn btn-sm btn-circle btn-ghost absolute right-2 top-2",
                        onclick="document.getElementById('analytics-modal').close()"
                    ),
                    cls="relative mb-4"
                ),

                # Статистика
                Div(
                    *stats_items,
                    cls="stats stats-vertical lg:stats-horizontal shadow w-full"
                ),

                # Кнопка закрытия
                Div(
                    Button(
                        "Закрыть",
                        type="button",
                        cls="btn btn-ghost btn-sm",
                        onclick="document.getElementById('analytics-modal').close()"
                    ),
                    cls="flex justify-end mt-4"
                ),

                cls="modal-box max-w-4xl"
            ),
            # Backdrop для закрытия при клике вне модального окна
            Form(
                Button(type="submit", cls="cursor-default"),
                method="dialog",
                cls="modal-backdrop"
            ),
            id="analytics-modal",
            cls="modal"
        ),
        id="analytics-modal-container"
    )
