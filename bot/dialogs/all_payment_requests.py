"""Диалог просмотра всех запросов на оплату (Billing контакты)"""

import logging
from typing import Any
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select, Row
from aiogram_dialog.widgets.text import Const, Format

from bot.states import AllPaymentRequests
from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus

logger = logging.getLogger(__name__)

# ============ Data Getters ============

async def get_all_requests_list_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает список всех запросов на оплату"""
    # Получаем фильтр из dialog_data (если есть)
    status_filter = dialog_manager.dialog_data.get("status_filter")

    async with get_session() as session:
        # Получаем все запросы
        all_requests = await PaymentRequestCRUD.get_all_payment_requests(session)

        # Применяем фильтр если есть
        if status_filter and status_filter != "all":
            if status_filter == "scheduled":
                # Фильтр для запланированных (оба статуса)
                all_requests = [
                    r for r in all_requests
                    if r.status in [PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE]
                ]
            else:
                try:
                    filter_status = PaymentRequestStatus(status_filter)
                    all_requests = [r for r in all_requests if r.status == filter_status]
                except ValueError:
                    pass  # Оставляем все запросы

        # Форматируем для отображения
        formatted_requests = []
        for req in all_requests:
            # Эмодзи статуса
            status_emoji = {
                PaymentRequestStatus.PENDING: "⏳",
                PaymentRequestStatus.SCHEDULED_TODAY: "📅",
                PaymentRequestStatus.SCHEDULED_DATE: "📅",
                PaymentRequestStatus.PAID: "✅",
                PaymentRequestStatus.CANCELLED: "❌",
            }

            # Краткое описание
            status_short = {
                PaymentRequestStatus.PENDING: "Ожидает",
                PaymentRequestStatus.SCHEDULED_TODAY: "Сегодня",
                PaymentRequestStatus.SCHEDULED_DATE: f"На {req.scheduled_date.strftime('%d.%m') if req.scheduled_date else '?'}",
                PaymentRequestStatus.PAID: "Оплачено",
                PaymentRequestStatus.CANCELLED: "Отменено",
            }

            formatted_requests.append({
                "id": req.id,
                "title": req.title[:25] + "..." if len(req.title) > 25 else req.title,
                "amount": req.amount,
                "creator": req.created_by.display_name[:15] if req.created_by else "?",
                "status_emoji": status_emoji.get(req.status, "❓"),
                "status_text": status_short.get(req.status, "?"),
                "created_at": req.created_at.strftime("%d.%m"),
            })

    return {
        "requests": formatted_requests,
        "count": len(formatted_requests),
        "current_filter": status_filter or "all",
    }


async def get_all_request_details_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает детали конкретного запроса (для billing)"""
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
            PaymentRequestStatus.SCHEDULED_TODAY: "📅 Оплачу сегодня",
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
            "created_by": payment_request.created_by.display_name,
            "created_at": payment_request.created_at.strftime("%d.%m.%Y %H:%M"),
            "has_invoice": payment_request.invoice_file_id is not None,
            "invoice_file_id": payment_request.invoice_file_id,
            "processing_by": payment_request.processing_by.display_name if payment_request.processing_by else None,
            "paid_by": payment_request.paid_by.display_name if payment_request.paid_by else None,
            "paid_at": payment_request.paid_at.strftime("%d.%m.%Y %H:%M") if payment_request.paid_at else None,
            "has_payment_proof": payment_request.payment_proof_file_id is not None,
            "payment_proof_file_id": payment_request.payment_proof_file_id,
            "status_raw": payment_request.status,
            # Можно ли выполнять действия
            "can_mark_paid": payment_request.status in [PaymentRequestStatus.PENDING, PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE],
            "can_schedule": payment_request.status == PaymentRequestStatus.PENDING,
            "can_cancel": payment_request.status in [PaymentRequestStatus.PENDING, PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE],
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
    """Фильтр: запланированные"""
    # Получаем оба статуса: SCHEDULED_TODAY и SCHEDULED_DATE
    manager.dialog_data["status_filter"] = "scheduled"
    await manager.update({})


async def on_filter_paid(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Фильтр: оплаченные"""
    manager.dialog_data["status_filter"] = PaymentRequestStatus.PAID.value
    await manager.update({})


async def on_all_request_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработчик выбора запроса из списка"""
    manager.dialog_data["selected_request_id"] = int(item_id)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.view_details)


async def on_download_invoice_billing(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправляет счет billing контакту"""
    data = await get_all_request_details_data(manager)

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


async def on_download_proof_billing(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправляет платежку billing контакту"""
    data = await get_all_request_details_data(manager)

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


async def on_back_to_all_list(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к списку всех запросов"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.list)


# ============ Dialog Windows ============

# Окно 1: Список всех запросов
all_list_window = Window(
    Const("💰 <b>Все запросы на оплату</b>\n"),
    Format("Показано запросов: {count}\n", when="count"),
    Const("\nЗапросов на оплату пока нет.", when=lambda data, widget, manager: data.get("count", 0) == 0),

    # Фильтры
    Row(
        Button(
            Const("📋 Все"),
            id="filter_all_billing",
            on_click=on_filter_all,
            when=lambda data, widget, manager: data.get("current_filter") != "all",
        ),
        Button(
            Const("⏳ Ожидают"),
            id="filter_pending_billing",
            on_click=on_filter_pending,
            when=lambda data, widget, manager: data.get("current_filter") != PaymentRequestStatus.PENDING.value,
        ),
        Button(
            Const("✅ Оплачены"),
            id="filter_paid_billing",
            on_click=on_filter_paid,
            when=lambda data, widget, manager: data.get("current_filter") != PaymentRequestStatus.PAID.value,
        ),
        when="count",
    ),

    # Список запросов
    ScrollingGroup(
        Select(
            Format("{item[status_emoji]} #{item[id]} {item[title]}\n{item[amount]} ₽ • {item[creator]} • {item[created_at]}"),
            id="all_request_select",
            item_id_getter=lambda x: str(x["id"]),
            items="requests",
            on_click=on_all_request_selected,
        ),
        id="all_requests_scroll",
        width=1,
        height=6,
        when="count",
    ),

    Cancel(Const("🏠 Главное меню")),
    state=AllPaymentRequests.list,
    getter=get_all_requests_list_data,
)

# Окно 2: Детали запроса (для billing)
all_details_window = Window(
    Format(
        "💰 <b>Запрос на оплату #{id}</b>\n\n"
        "<b>Статус:</b> {status}\n"
        "<b>Название:</b> {title}\n"
        "<b>Сумма:</b> {amount} ₽\n"
        "<b>Комментарий:</b> {comment}\n\n"
        "<b>Создал:</b> {created_by}\n"
        "<b>Дата создания:</b> {created_at}\n"
    ),
    Format("<b>Взял в работу:</b> {processing_by}\n", when="processing_by"),
    Format("<b>Оплатил:</b> {paid_by}\n<b>Дата оплаты:</b> {paid_at}\n", when="paid_by"),
    Format("\n📎 Счет: {'Прикреплен' if has_invoice else 'Не прикреплен'}"),
    Format("\n📎 Платежка: {'Прикреплена' if has_payment_proof else 'Не прикреплена'}"),

    Button(
        Const("📥 Скачать счет"),
        id="download_invoice_billing",
        on_click=on_download_invoice_billing,
        when="has_invoice",
    ),
    Button(
        Const("📥 Скачать платежку"),
        id="download_proof_billing",
        on_click=on_download_proof_billing,
        when="has_payment_proof",
    ),
    Const(
        "\n💡 <i>Для действий используйте inline кнопки в уведомлениях</i>",
        when=lambda data, widget, manager: data.get("can_mark_paid") or data.get("can_schedule") or data.get("can_cancel"),
    ),
    Button(
        Const("⬅️ Назад к списку"),
        id="back_to_all_list",
        on_click=on_back_to_all_list,
    ),
    Cancel(Const("🏠 Главное меню")),

    state=AllPaymentRequests.view_details,
    getter=get_all_request_details_data,
)


# Создаем диалог
all_payment_requests_dialog = Dialog(
    all_list_window,
    all_details_window,
)
