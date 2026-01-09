"""Handlers для диалога просмотра своих запросов на оплату"""

import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select

from .states import MyPaymentRequests
from bot.database import get_session, PaymentRequestCRUD, BillingNotificationCRUD
from bot.handlers.payments.callbacks import format_payment_request_message, get_payment_request_keyboard
from .getters import get_request_details_data

logger = logging.getLogger(__name__)


# ============ Filter Button Handlers ============

async def on_filter_active(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: активные запросы"""
    manager.dialog_data["status_filter"] = "active"
    await manager.update({})


async def on_filter_completed(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: завершенные запросы"""
    manager.dialog_data["status_filter"] = "completed"
    await manager.update({})


async def on_filter_cancelled(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: отмененные запросы"""
    manager.dialog_data["status_filter"] = "cancelled"
    await manager.update({})


# ============ Selection Handler ============

async def on_request_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработчик выбора запроса из списка"""
    manager.dialog_data["selected_request_id"] = int(item_id)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(MyPaymentRequests.view_details)


# ============ Document Download Handlers ============

async def on_download_invoice(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправляет счет пользователю"""
    data = await get_request_details_data(manager, user=manager.middleware_data.get("user"))

    if data.get("has_invoice") and data.get("invoice_file_id"):
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Скрыть документ", callback_data="hide_document")]
            ])

            await callback.bot.send_document(
                chat_id=callback.from_user.id,
                document=data["invoice_file_id"],
                caption=f"📎 Счет к запросу #{data['id']}",
                reply_markup=keyboard,
            )
            await callback.answer("Счет отправлен")
        except Exception as e:
            logger.error(f"Error sending invoice: {e}")
            await callback.answer("❌ Ошибка при отправке счета", show_alert=True)
    else:
        await callback.answer("Счет не прикреплен", show_alert=True)


async def on_download_proof(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправляет платежку пользователю"""
    data = await get_request_details_data(manager, user=manager.middleware_data.get("user"))

    if data.get("has_payment_proof") and data.get("payment_proof_file_id"):
        try:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Скрыть документ", callback_data="hide_document")]
            ])

            await callback.bot.send_document(
                chat_id=callback.from_user.id,
                document=data["payment_proof_file_id"],
                caption=f"📎 Платежка к запросу #{data['id']}",
                reply_markup=keyboard,
            )
            await callback.answer("Платежка отправлена")
        except Exception as e:
            logger.error(f"Error sending payment proof: {e}")
            await callback.answer("❌ Ошибка при отправке платежки", show_alert=True)
    else:
        await callback.answer("Платежка не прикреплена", show_alert=True)


# ============ Action Handlers ============

async def on_cancel_request(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отменяет pending запрос"""
    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.cancel_payment_request(session, request_id)

        if not payment_request:
            await callback.answer("❌ Ошибка при отмене запроса", show_alert=True)
            return

        # Обновляем сообщения у ВСЕХ billing контактов
        billing_notifications = await BillingNotificationCRUD.get_billing_notifications(session, payment_request.id)

        new_text = format_payment_request_message(
            request_id=payment_request.id,
            title=payment_request.title,
            amount=payment_request.amount,
            comment=payment_request.comment,
            created_by_name=payment_request.created_by.display_name,
            status=payment_request.status,
            created_at=payment_request.created_at,
        )

        for notification in billing_notifications:
            try:
                await callback.bot.edit_message_text(
                    chat_id=notification.chat_id,
                    message_id=notification.message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing notification {notification.id}: {e}")

        # Обновляем сообщение Worker (если есть worker_message_id из success окна)
        if payment_request.worker_message_id and payment_request.created_by.telegram_id:
            try:
                worker_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                )

                await callback.bot.edit_message_text(
                    chat_id=payment_request.created_by.telegram_id,
                    message_id=payment_request.worker_message_id,
                    text=worker_text,
                )
            except Exception as e:
                logger.error(f"Error updating worker message: {e}")

    await callback.answer("✅ Запрос отменен", show_alert=True)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(MyPaymentRequests.list)


async def on_back_to_list(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к списку запросов"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(MyPaymentRequests.list)
