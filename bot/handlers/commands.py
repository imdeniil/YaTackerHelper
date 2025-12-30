"""Обработчики команд бота."""

from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram_dialog import DialogManager, StartMode

from bot.states import MainMenu

router = Router(name="commands")


@router.message(CommandStart())
async def cmd_start(message: Message, dialog_manager: DialogManager):
    """
    Обработчик команды /start.

    Args:
        message: Сообщение от пользователя
        dialog_manager: Менеджер диалогов
    """
    await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)


@router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Обработчик команды /help.

    Args:
        message: Сообщение от пользователя
    """
    help_text = """
🤖 <b>YaTacker Helper Bot</b>

Бот для клонирования проектов из Yandex Tracker со всеми задачами, подзадачами, чеклистами, связями и комментариями.

<b>📋 Доступные команды:</b>

/start - Главное меню
/help - Показать эту справку
/cancel - Отменить текущую операцию

<b>🔧 Возможности:</b>

• Клонирование проектов с полной иерархией
• Рекурсивный обход всех подзадач
• Сохранение всех связей между задачами
• Восстановление чеклистов и комментариев
• Отображение прогресса выполнения

<b>📖 Как использовать:</b>

1. Нажмите /start для открытия главного меню
2. Выберите "Клонировать проект"
3. Следуйте инструкциям бота
4. Дождитесь завершения клонирования

<b>⚙️ Технические детали:</b>

Бот использует Yandex Tracker API для работы с проектами.
Все данные берутся из вашей организации в Tracker.

Если возникли проблемы - обратитесь к администратору.
"""
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, dialog_manager: DialogManager, state: FSMContext):
    """
    Обработчик команды /cancel.

    Args:
        message: Сообщение от пользователя
        dialog_manager: Менеджер диалогов
        state: FSM контекст
    """
    # Проверяем есть ли активный FSM state (для payment callbacks)
    current_state = await state.get_state()

    # Проверяем есть ли активный диалог
    has_dialog = dialog_manager.has_context()

    if current_state or has_dialog:
        # Очищаем FSM state если есть
        if current_state:
            await state.clear()

        # Закрываем диалог если есть
        if has_dialog:
            await dialog_manager.done()

        await message.answer("❌ Текущая операция отменена")
    else:
        await message.answer("ℹ️ Нет активных операций")


@router.callback_query(F.data == "goto_main_menu")
async def goto_main_menu(callback: CallbackQuery, dialog_manager: DialogManager):
    """
    Обработчик кнопки возврата в главное меню.

    Args:
        callback: Callback от кнопки
        dialog_manager: Менеджер диалогов
    """
    await callback.answer()

    # Закрываем текущий диалог если есть
    if dialog_manager.has_context():
        await dialog_manager.done()

    # Запускаем главное меню
    await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)
