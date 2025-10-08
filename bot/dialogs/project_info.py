"""Диалог для просмотра информации о проекте."""

from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Back
from aiogram_dialog.widgets.text import Const

from bot.states import ProjectInfo


# Заглушка для диалога информации о проекте
# TODO: Реализовать полноценный диалог
project_info_dialog = Dialog(
    Window(
        Const("ℹ️ Информация о проекте\n"),
        Const("Функция в разработке..."),
        Back(Const("◀️ Назад")),
        state=ProjectInfo.select_project,
    ),
)
