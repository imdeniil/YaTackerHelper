"""Диалог просмотра всех запросов на оплату (Billing контакты)"""

import logging
from typing import Any
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select, Row
from aiogram_dialog.widgets.text import Const, Format

from bot.states import AllPaymentRequests
from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus
from bot.handlers.payment_callbacks import UploadProof, CancelWithComment

logger = logging.getLogger(__name__)

# ============ Data Getters ============

async def get_all_requests_list_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает список всех запросов на оплату"""
    # Получаем фильтр из dialog_data (по умолчанию - активные)
    status_filter = dialog_manager.dialog_data.get("status_filter", "active")

    async with get_session() as session:
        # Получаем все запросы
        all_requests = await PaymentRequestCRUD.get_all_payment_requests(session)

        # Применяем фильтр
        if status_filter == "active":
            # Активные: все кроме PAID и CANCELLED
            requests = [
                r for r in all_requests
                if r.status not in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]
            ]
        elif status_filter == "completed":
            # Завершенные: только PAID
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.PAID]
        elif status_filter == "cancelled":
            # Отмененные: только CANCELLED
            requests = [r for r in all_requests if r.status == PaymentRequestStatus.CANCELLED]
        else:
            # На случай старых фильтров - показываем активные
            requests = [
                r for r in all_requests
                if r.status not in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]
            ]

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
        "total_count": len(all_requests),
        "current_filter": status_filter,
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
            "invoice_status": "Прикреплен" if payment_request.invoice_file_id else "Не прикреплен",
            "processing_by": payment_request.processing_by.display_name if payment_request.processing_by else None,
            "paid_by": payment_request.paid_by.display_name if payment_request.paid_by else None,
            "paid_at": payment_request.paid_at.strftime("%d.%m.%Y %H:%M") if payment_request.paid_at else None,
            "has_payment_proof": payment_request.payment_proof_file_id is not None,
            "payment_proof_file_id": payment_request.payment_proof_file_id,
            "payment_proof_status": "Прикреплена" if payment_request.payment_proof_file_id else "Не прикреплена",
            "status_raw": payment_request.status,
            # Можно ли выполнять действия
            "can_mark_paid": payment_request.status in [PaymentRequestStatus.PENDING, PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE],
            "can_schedule": payment_request.status == PaymentRequestStatus.PENDING,
            "can_cancel": payment_request.status in [PaymentRequestStatus.PENDING, PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE],
            # Можно ли оплатить досрочно (только запланированные запросы)
            "can_pay_early": payment_request.status in [PaymentRequestStatus.SCHEDULED_TODAY, PaymentRequestStatus.SCHEDULED_DATE],
            # Специфичные действия для PENDING
            "is_pending": payment_request.status == PaymentRequestStatus.PENDING,
        }


# ============ Button Handlers ============

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


async def on_download_proof_billing(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправляет платежку billing контакту"""
    data = await get_all_request_details_data(manager)

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


async def on_pay_early(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик досрочной оплаты запроса"""
    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос еще не оплачен и не отменен
        if payment_request.status in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

    # Получаем FSM context из event
    state: FSMContext = manager.middleware_data.get("state")
    if not state:
        await callback.answer("❌ Ошибка: не удалось получить FSM context", show_alert=True)
        return

    # Сохраняем message_id текущего диалогового сообщения
    dialog_message_id = callback.message.message_id

    # Сохраняем request_id в FSM state
    await state.set_state(UploadProof.waiting_for_document)
    await state.update_data(
        request_id=request_id,
        upload_proof_message_id=dialog_message_id
    )

    # Закрываем диалог
    await manager.done()

    # Редактируем ТО ЖЕ сообщение (не отправляем новое)
    await callback.message.edit_text(
        "📎 <b>Досрочная оплата запроса</b>\n\n"
        "Пожалуйста, отправьте документ с платежкой (скриншот или PDF).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отменить действие", callback_data=f"cancel_action:{request_id}")]
        ])
    )
    await callback.answer()


async def on_cancel_early(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик досрочной отмены запроса"""
    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос еще можно отменить
        if payment_request.status in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

    # Получаем FSM context из event
    state: FSMContext = manager.middleware_data.get("state")
    if not state:
        await callback.answer("❌ Ошибка: не удалось получить FSM context", show_alert=True)
        return

    # Сохраняем request_id в FSM state и запрашиваем комментарий
    await state.set_state(CancelWithComment.waiting_for_comment)

    # Закрываем диалог
    await manager.done()

    # Отправляем сообщение с запросом комментария и сохраняем его message_id
    sent_message = await callback.message.answer(
        f"❌ <b>Отмена запроса на оплату #{request_id}</b>\n\n"
        f"Пожалуйста, укажите причину отмены.\n"
        f"Этот комментарий увидит Worker.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отменить действие", callback_data=f"cancel_action:{request_id}")]
        ])
    )

    await state.update_data(
        request_id=request_id,
        cancel_request_message_id=sent_message.message_id
    )
    await callback.answer()


async def on_pay_now(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик кнопки 'Оплатить сейчас' для PENDING запросов"""
    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос в статусе PENDING
        if payment_request.status != PaymentRequestStatus.PENDING:
            await callback.answer("❌ Запрос не в статусе ожидания", show_alert=True)
            return

    # Получаем FSM context
    state: FSMContext = manager.middleware_data.get("state")
    if not state:
        await callback.answer("❌ Ошибка: не удалось получить FSM context", show_alert=True)
        return

    # Сохраняем message_id текущего диалогового сообщения
    dialog_message_id = callback.message.message_id

    # Сохраняем request_id в FSM state для последующей обработки
    await state.set_state(UploadProof.waiting_for_document)
    await state.update_data(
        request_id=request_id,
        upload_proof_message_id=dialog_message_id
    )

    # Закрываем диалог
    await manager.done()

    # Редактируем ТО ЖЕ сообщение (не отправляем новое)
    await callback.message.edit_text(
        "📎 <b>Оплата запроса</b>\n\n"
        "Пожалуйста, отправьте документ с платежкой (скриншот или PDF).",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отменить действие", callback_data=f"cancel_action:{request_id}")]
        ])
    )
    await callback.answer()


async def on_schedule_now(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик кнопки 'Запланировать' для PENDING запросов"""
    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос в статусе PENDING
        if payment_request.status != PaymentRequestStatus.PENDING:
            await callback.answer("❌ Запрос не в статусе ожидания", show_alert=True)
            return

    # Переходим в окно выбора даты
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.schedule_date)
    await callback.answer()


async def on_cancel_now(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик кнопки 'Отменить запрос' для PENDING запросов"""
    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос можно отменить
        if payment_request.status in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

    # Получаем FSM context
    state: FSMContext = manager.middleware_data.get("state")
    if not state:
        await callback.answer("❌ Ошибка: не удалось получить FSM context", show_alert=True)
        return

    # Запрашиваем комментарий об отмене
    await state.set_state(CancelWithComment.waiting_for_comment)

    # Закрываем диалог
    await manager.done()

    # Отправляем сообщение с запросом комментария
    sent_message = await callback.message.answer(
        f"❌ <b>Отмена запроса на оплату #{request_id}</b>\n\n"
        f"Пожалуйста, укажите причину отмены.\n"
        f"Этот комментарий увидит Worker.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отменить действие", callback_data=f"cancel_action:{request_id}")]
        ])
    )

    await state.update_data(
        request_id=request_id,
        cancel_request_message_id=sent_message.message_id
    )
    await callback.answer()


async def on_schedule_today(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик планирования на сегодня"""
    request_id = manager.dialog_data.get("selected_request_id")
    user = manager.middleware_data.get("user")

    if not request_id or not user:
        await callback.answer("❌ Ошибка: недостаточно данных", show_alert=True)
        return

    async with get_session() as session:
        from bot.database import BillingNotificationCRUD
        from bot.handlers.payment_callbacks import format_payment_request_message, get_payment_request_keyboard

        # Планируем на сегодня и устанавливаем processing_by
        payment_request = await PaymentRequestCRUD.schedule_payment(
            session=session,
            request_id=request_id,
            processing_by_id=user.id,  # Устанавливаем кто взял в работу
            is_today=True,
        )

        if not payment_request:
            await callback.answer("❌ Ошибка при планировании", show_alert=True)
            return

        # Обновляем сообщения у всех billing контактов
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

    await callback.answer("✅ Запланировано на сегодня", show_alert=True)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.view_details)


async def on_select_custom_date(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Обработчик выбора произвольной даты"""
    from bot.handlers.payment_callbacks import SelectDate

    request_id = manager.dialog_data.get("selected_request_id")

    if not request_id:
        await callback.answer("❌ Ошибка: ID запроса не найден", show_alert=True)
        return

    # Получаем FSM context
    state: FSMContext = manager.middleware_data.get("state")
    if not state:
        await callback.answer("❌ Ошибка: не удалось получить FSM context", show_alert=True)
        return

    # Сохраняем request_id в FSM state
    await state.set_state(SelectDate.waiting_for_date)
    await state.update_data(request_id=request_id)

    # Закрываем диалог
    await manager.done()

    # Отправляем инструкцию с отмечанием сообщения для редактирования
    sent_message = await callback.message.answer(
        "📅 <b>Планирование оплаты</b>\n\n"
        "Введите дату в формате ДД.ММ.ГГГГ\n"
        "Например: 31.12.2025\n\n"
        "Для отмены отправьте /cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Отменить действие", callback_data=f"cancel_action:{request_id}")]
        ])
    )

    # Сохраняем message_id для возможного редактирования
    await state.update_data(
        request_id=request_id,
        select_date_message_id=sent_message.message_id
    )
    await callback.answer()


async def on_back_from_schedule(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к деталям запроса из окна планирования"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.view_details)


async def on_back_to_all_list(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к списку всех запросов"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.list)


# ============ Dialog Windows ============

# Окно 1: Список всех запросов
all_list_window = Window(
    Const("💰 <b>Все запросы на оплату</b>\n"),
    Format("Всего запросов: {total_count}\nПоказано: {count}\n", when="count"),
    Const(
        "\n<i>Статусы:</i>\n⏳ Ожидает\n📅 Запланировано\n✅ Оплачено\n❌ Отменено\n---------------------------------------",
        when="count"
    ),
    Const("\nЗапросов на оплату пока нет.", when=lambda data, widget, manager: data.get("count", 0) == 0),

    # Список запросов
    ScrollingGroup(
        Select(
            Format("{item[status_emoji]} #{item[id]}|{item[amount]}|{item[title]}"),
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

    # Фильтры (показываем только 2 кнопки для других фильтров)
    Row(
        Button(
            Const("✅ Завершенные"),
            id="filter_completed_billing",
            on_click=on_filter_completed,
            when=lambda data, widget, manager: data.get("current_filter") != "completed",
        ),
        Button(
            Const("❌ Отмененные"),
            id="filter_cancelled_billing",
            on_click=on_filter_cancelled,
            when=lambda data, widget, manager: data.get("current_filter") != "cancelled",
        ),
        Button(
            Const("📋 Активные"),
            id="filter_active_billing",
            on_click=on_filter_active,
            when=lambda data, widget, manager: data.get("current_filter") != "active",
        ),
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
    Format("\n📎 Счет: {invoice_status}"),
    Format("\n📎 Платежка: {payment_proof_status}"),

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
    # Кнопки для PENDING запросов
    Button(
        Const("✅ Оплатить сейчас"),
        id="pay_now",
        on_click=on_pay_now,
        when="is_pending",
    ),
    Button(
        Const("📅 Запланировать"),
        id="schedule_now",
        on_click=on_schedule_now,
        when="is_pending",
    ),
    Button(
        Const("❌ Отменить запрос"),
        id="cancel_now_pending",
        on_click=on_cancel_now,
        when="is_pending",
    ),
    # Кнопки для запланированных запросов
    Button(
        Const("✅ Оплатить досрочно"),
        id="pay_early",
        on_click=on_pay_early,
        when="can_pay_early",
    ),
    Button(
        Const("❌ Отменить запрос"),
        id="cancel_early",
        on_click=on_cancel_early,
        when=lambda data, widget, manager: data.get("can_pay_early"),  # Показываем только для запланированных
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

# Окно 3: Выбор даты для планирования
schedule_date_window = Window(
    Format(
        "📅 <b>Планирование оплаты запроса #{id}</b>\n\n"
        "<b>Название:</b> {title}\n"
        "<b>Сумма:</b> {amount} ₽\n\n"
        "Выберите когда планируете оплатить:"
    ),
    Button(
        Const("📅 Сегодня"),
        id="schedule_today",
        on_click=on_schedule_today,
    ),
    Button(
        Const("📅 Выбрать дату"),
        id="select_custom_date",
        on_click=on_select_custom_date,
    ),
    Button(
        Const("⬅️ Назад"),
        id="back_from_schedule",
        on_click=on_back_from_schedule,
    ),
    Cancel(Const("🏠 Главное меню")),

    state=AllPaymentRequests.schedule_date,
    getter=get_all_request_details_data,
)


# Создаем диалог
all_payment_requests_dialog = Dialog(
    all_list_window,
    all_details_window,
    schedule_date_window,
)
