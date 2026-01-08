"""Обработчики callback для утреннего списка PENDING платежей"""

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus
from bot.handlers.payment_callbacks import (
    format_payment_request_message,
    get_payment_request_keyboard,
    UploadProof,
    CancelWithComment,
)
from bot.services.payment_reminders import _build_pending_list_keyboard, PENDING_PAGE_SIZE

logger = logging.getLogger(__name__)

# Router для callback handlers утреннего списка
pending_list_router = Router()


@pending_list_router.callback_query(F.data.startswith("pending_page:"))
async def on_pending_page(callback: CallbackQuery):
    """Обработчик пагинации в утреннем списке PENDING"""
    page = int(callback.data.split(":")[1])

    async with get_session() as session:
        # Получаем все PENDING запросы
        pending_requests = await PaymentRequestCRUD.get_all_payment_requests(
            session, status_filter=PaymentRequestStatus.PENDING.value
        )

        if not pending_requests:
            await callback.answer("Нет ожидающих платежей", show_alert=True)
            return

        # Сортируем по дате создания (старые первые)
        pending_requests.sort(key=lambda x: x.created_at)

        total_pages = (len(pending_requests) + PENDING_PAGE_SIZE - 1) // PENDING_PAGE_SIZE

        # Проверяем корректность страницы
        if page < 0 or page >= total_pages:
            await callback.answer("Страница не существует", show_alert=True)
            return

        # Получаем запросы для текущей страницы
        start_idx = page * PENDING_PAGE_SIZE
        end_idx = start_idx + PENDING_PAGE_SIZE
        page_requests = pending_requests[start_idx:end_idx]

        total_amount = sum(
            float(req.amount.replace(" ", "").replace(",", "."))
            for req in pending_requests
            if req.amount
        )

        # Формируем сообщение
        message_text = (
            f"🌅 <b>Доброе утро! Ожидающие платежи</b>\n\n"
            f"📊 Всего запросов: <b>{len(pending_requests)}</b>\n"
            f"💰 Общая сумма: <b>{total_amount:,.0f} ₽</b>\n\n"
            f"Выберите запрос для действия:"
        )

        keyboard = _build_pending_list_keyboard(
            page_requests, page, total_pages, callback.from_user.id
        )

        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard,
        )
        await callback.answer()


@pending_list_router.callback_query(F.data == "pending_noop")
async def on_pending_noop(callback: CallbackQuery):
    """Обработчик нажатия на индикатор страницы (ничего не делает)"""
    await callback.answer()


@pending_list_router.callback_query(F.data.startswith("pending_select:"))
async def on_pending_select(callback: CallbackQuery):
    """Обработчик выбора платежа из утреннего списка"""
    request_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос еще в статусе PENDING
        if payment_request.status != PaymentRequestStatus.PENDING:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

        # Формируем детальное сообщение
        message_text = format_payment_request_message(
            request_id=payment_request.id,
            title=payment_request.title,
            amount=payment_request.amount,
            comment=payment_request.comment,
            created_by_name=payment_request.created_by.display_name,
            status=payment_request.status,
            created_at=payment_request.created_at,
        )

        # Клавиатура с действиями
        keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard,
        )
        await callback.answer()
