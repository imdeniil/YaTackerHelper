"""Диалог просмотра своих запросов на оплату (Worker)"""

import logging
from typing import Any
from datetime import datetime
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select, Row
from aiogram_dialog.widgets.text import Const, Format, Case

from bot.states import MyPaymentRequests
from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus, UserCRUD
from bot.handlers.payment_callbacks import format_payment_request_message, get_payment_request_keyboard

logger = logging.getLogger(__name__)

# ============ Data Getters ============

async def get_my_requests_list_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает список запросов на оплату пользователя"""
    user = kwargs.get("user")
    if not user:
        return {"requests": [], "count": 0}

    # Получаем фильтр из dialog_data (если есть)
    status_filter = dialog_manager.dialog_data.get("status_filter")

    async with get_session() as session:
        # Получаем все запросы пользователя
        all_requests = await PaymentRequestCRUD.get_user_payment_requests(session, user.id)

        # Применяем фильтр если есть
        if status_filter and status_filter != "all":
            if status_filter == "scheduled":
                # Фильтр для запланированных (оба статуса)
                requests = [
                    r for r in all_requests
                    if r.status in [PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE]
                ]
            else:
                try:
                    filter_status = PaymentRequestStatus(status_filter)
                    requests = [r for r in all_requests if r.status == filter_status]
                except ValueError:
                    requests = all_requests
        else:
            requests = all_requests

        # Форматируем для отображения
        formatted_requests = []
        for req in requests:
            # Эмодзи статуса
            status_emoji = {
                PaymentRequestStatus.PENDING: "⏳",
                PaymentRequestStatus.SCHEDULED_TODAY: "📅",
                PaymentRequestStatus.SCHEDULED_DATE: "📅",
                PaymentRequestStatus.PAID: "✅",
                PaymentRequestStatus.CANCELLED: "❌",
            }

            # Краткое описание статуса
            status_short = {
                PaymentRequestStatus.PENDING: "Ожидает",
                PaymentRequestStatus.SCHEDULED_TODAY: "Сегодня",
                PaymentRequestStatus.SCHEDULED_DATE: f"На {req.scheduled_date.strftime('%d.%m') if req.scheduled_date else '?'}",
                PaymentRequestStatus.PAID: "Оплачено",
                PaymentRequestStatus.CANCELLED: "Отменено",
            }

            formatted_requests.append({
                "id": req.id,
                "title": req.title[:30] + "..." if len(req.title) > 30 else req.title,
                "amount": req.amount,
                "status_emoji": status_emoji.get(req.status, "❓"),
                "status_text": status_short.get(req.status, "?"),
                "created_at": req.created_at.strftime("%d.%m.%Y"),
            })

    return {
        "requests": formatted_requests,
        "count": len(formatted_requests),
        "total_count": len(all_requests),
        "current_filter": status_filter or "all",
    }


async def get_request_details_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает детали конкретного запроса"""
    request_id = dialog_manager.dialog_data.get("selected_request_id")

    if not request_id:
        return {"error": "Request ID not found"}

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            return {"error": "Request not found"}

        # Форматируем статус
        status_text_map = {
            PaymentRequestStatus.PENDING: "⏳ Ожидает оплаты",
            PaymentRequestStatus.SCHEDULED_TODAY: "📅 Оплатят сегодня",
            PaymentRequestStatus.SCHEDULED_DATE: f"📅 Запланировано на {payment_request.scheduled_date.strftime('%d.%m.%Y') if payment_request.scheduled_date else '?'}",
            PaymentRequestStatus.PAID: "✅ Оплачено",
            PaymentRequestStatus.CANCELLED: "❌ Отменено",
        }

        return {
            "id": payment_request.id,
            "title": payment_request.title,
            "amount": payment_request.amount,
            "comment": payment_request.comment,
            "status": status_text_map.get(payment_request.status, "Неизвестно"),
            "created_at": payment_request.created_at.strftime("%d.%m.%Y %H:%M"),
            "has_invoice": payment_request.invoice_file_id is not None,
            "invoice_file_id": payment_request.invoice_file_id,
            "invoice_status": "Прикреплен" if payment_request.invoice_file_id else "Не прикреплен",
            "processing_by": payment_request.processing_by.display_name if payment_request.processing_by else None,
            "paid_by": payment_request.paid_by.display_name if payment_request.paid_by else None,
            "paid_at": payment_request.paid_at.strftime("%d.%m.%Y %H:%M") if payment_request.paid_at else None,
            "has_payment_proof": payment_request.payment_proof_file_id is not None,
            "payment_proof_file_id": payment_request.payment_proof_file_id,
            "payment_proof_status": "Прикреплена" if payment_request.payment_proof_file_id else "Не прикреплена",
            "can_cancel": payment_request.status == PaymentRequestStatus.PENDING,
            "status_raw": payment_request.status,
        }


# ============ Button Handlers ============

async def on_filter_all(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: все запросы"""
    manager.dialog_data["status_filter"] = "all"
    await manager.update({})


async def on_filter_pending(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: ожидающие"""
    manager.dialog_data["status_filter"] = PaymentRequestStatus.PENDING.value
    await manager.update({})


async def on_filter_scheduled(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: запланированные (today + date)"""
    manager.dialog_data["status_filter"] = "scheduled"
    await manager.update({})


async def on_filter_paid(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: оплаченные"""
    manager.dialog_data["status_filter"] = PaymentRequestStatus.PAID.value
    await manager.update({})


async def on_request_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработчик выбора запроса из списка"""
    manager.dialog_data["selected_request_id"] = int(item_id)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(MyPaymentRequests.view_details)


async def on_download_invoice(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправляет счет пользователю"""
    data = await get_request_details_data(manager, user=manager.middleware_data.get("user"))

    if data.get("has_invoice") and data.get("invoice_file_id"):
        try:
            await callback.bot.send_document(
                chat_id=callback.from_user.id,
                document=data["invoice_file_id"],
                caption=f"📎 Счет к запросу #{data['id']}",
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
            await callback.bot.send_document(
                chat_id=callback.from_user.id,
                document=data["payment_proof_file_id"],
                caption=f"📎 Платежка к запросу #{data['id']}",
            )
            await callback.answer("Платежка отправлена")
        except Exception as e:
            logger.error(f"Error sending payment proof: {e}")
            await callback.answer("❌ Ошибка при отправке платежки", show_alert=True)
    else:
        await callback.answer("Платежка не прикреплена", show_alert=True)


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

        # Обновляем сообщение у billing контакта (если взят в работу) или уведомляем всех
        new_text = format_payment_request_message(
            request_id=payment_request.id,
            title=payment_request.title,
            amount=payment_request.amount,
            comment=payment_request.comment,
            created_by_name=payment_request.created_by.display_name,
            status=payment_request.status,
            created_at=payment_request.created_at,
        )

        if payment_request.processing_by and payment_request.processing_by.telegram_id and payment_request.billing_message_id:
            # Если запрос был взят в работу - обновляем сообщение у processing_by
            try:
                await callback.bot.edit_message_text(
                    chat_id=payment_request.processing_by.telegram_id,
                    message_id=payment_request.billing_message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing message: {e}")
        else:
            # Если запрос не был взят в работу - отправляем уведомление всем billing контактам
            billing_contacts = await UserCRUD.get_billing_contacts(session)
            keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

            for billing_contact in billing_contacts:
                if billing_contact.telegram_id:
                    try:
                        await callback.bot.send_message(
                            chat_id=billing_contact.telegram_id,
                            text=f"❌ <b>Запрос отменен Worker</b>\n\n{new_text}",
                            reply_markup=keyboard,
                        )
                    except Exception as e:
                        logger.error(f"Error notifying billing contact {billing_contact.telegram_username}: {e}")

    await callback.answer("✅ Запрос отменен", show_alert=True)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(MyPaymentRequests.list)


async def on_back_to_list(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к списку запросов"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(MyPaymentRequests.list)


# ============ Dialog Windows ============

# Окно 1: Список запросов
list_window = Window(
    Const("💰 <b>Мои запросы на оплату</b>\n"),
    Format("Всего запросов: {total_count}\nПоказано: {count}\n", when="count"),
    Const("\nУ вас пока нет запросов на оплату.", when=lambda data, widget, manager: data.get("count", 0) == 0),

    # Фильтры
    Row(
        Button(
            Const("📋 Все"),
            id="filter_all",
            on_click=on_filter_all,
            when=lambda data, widget, manager: data.get("current_filter") != "all",
        ),
        Button(
            Const("⏳ Ожидают"),
            id="filter_pending",
            on_click=on_filter_pending,
            when=lambda data, widget, manager: data.get("current_filter") != PaymentRequestStatus.PENDING.value,
        ),
        Button(
            Const("✅ Оплачены"),
            id="filter_paid",
            on_click=on_filter_paid,
            when=lambda data, widget, manager: data.get("current_filter") != PaymentRequestStatus.PAID.value,
        ),
        when="count",
    ),

    # Список запросов
    ScrollingGroup(
        Select(
            Format("{item[status_emoji]} {item[title]} - {item[amount]} ₽\n{item[status_text]} • {item[created_at]}"),
            id="request_select",
            item_id_getter=lambda x: str(x["id"]),
            items="requests",
            on_click=on_request_selected,
        ),
        id="requests_scroll",
        width=1,
        height=6,
        when="count",
    ),

    Cancel(Const("🏠 Главное меню")),
    state=MyPaymentRequests.list,
    getter=get_my_requests_list_data,
)

# Окно 2: Детали запроса
details_window = Window(
    Format(
        "💰 <b>Запрос на оплату #{id}</b>\n\n"
        "<b>Статус:</b> {status}\n"
        "<b>Название:</b> {title}\n"
        "<b>Сумма:</b> {amount} ₽\n"
        "<b>Комментарий:</b> {comment}\n\n"
        "<b>Дата создания:</b> {created_at}\n"
    ),
    Format("<b>Взял в работу:</b> {processing_by}\n", when="processing_by"),
    Format("<b>Оплатил:</b> {paid_by}\n<b>Дата оплаты:</b> {paid_at}\n", when="paid_by"),
    Format("\n📎 Счет: {invoice_status}"),
    Format("\n📎 Платежка: {payment_proof_status}"),

    Button(
        Const("📥 Скачать счет"),
        id="download_invoice",
        on_click=on_download_invoice,
        when="has_invoice",
    ),
    Button(
        Const("📥 Скачать платежку"),
        id="download_proof",
        on_click=on_download_proof,
        when="has_payment_proof",
    ),
    Button(
        Const("❌ Отменить запрос"),
        id="cancel_request",
        on_click=on_cancel_request,
        when="can_cancel",
    ),
    Button(
        Const("⬅️ Назад к списку"),
        id="back_to_list",
        on_click=on_back_to_list,
    ),
    Cancel(Const("🏠 Главное меню")),

    state=MyPaymentRequests.view_details,
    getter=get_request_details_data,
)


# Создаем диалог
my_payment_requests_dialog = Dialog(
    list_window,
    details_window,
)
