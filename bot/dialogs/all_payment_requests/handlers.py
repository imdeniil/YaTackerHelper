"""Button handlers для диалога просмотра всех запросов на оплату"""

import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select

from .states import AllPaymentRequests
from bot.database import get_session, PaymentRequestCRUD, PaymentRequestStatus
from bot.handlers.payments.callbacks import UploadProof, CancelWithComment
from .getters import get_all_request_details_data

logger = logging.getLogger(__name__)


# ============ Фильтры ============

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


# ============ Навигация ============

async def on_all_request_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработчик выбора запроса из списка"""
    manager.dialog_data["selected_request_id"] = int(item_id)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.view_details)


async def on_back_to_all_list(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к списку всех запросов"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.list)


async def on_back_from_schedule(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат к деталям запроса из окна планирования"""
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(AllPaymentRequests.view_details)


# ============ Действия с документами ============

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


# ============ Действия с запросами (оплата, планирование, отмена) ============

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
        from bot.handlers.payments.callbacks import format_payment_request_message, get_payment_request_keyboard

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
    from bot.handlers.payments.callbacks import SelectDate

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
