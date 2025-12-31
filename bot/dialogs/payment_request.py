"""Диалог создания запроса на оплату (Worker)"""

import logging
from typing import Any
from aiogram import F
from aiogram.types import Message, CallbackQuery, ContentType
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Cancel, Column
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from bot.states import PaymentRequestCreation, MainMenu
from bot.database import get_session, PaymentRequestCRUD, UserCRUD, BillingNotificationCRUD
from bot.handlers.payment_callbacks import format_payment_request_message, get_payment_request_keyboard

logger = logging.getLogger(__name__)

# ============ Data Getters ============

async def get_title_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна ввода названия"""
    return {
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_amount_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна ввода суммы"""
    title = dialog_manager.dialog_data.get("title", "")
    return {
        "title": title,
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_comment_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна ввода комментария"""
    title = dialog_manager.dialog_data.get("title", "")
    amount = dialog_manager.dialog_data.get("amount", "")
    return {
        "title": title,
        "amount": amount,
        "error": dialog_manager.dialog_data.get("error"),
    }


async def get_attach_invoice_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна прикрепления счета"""
    title = dialog_manager.dialog_data.get("title", "")
    amount = dialog_manager.dialog_data.get("amount", "")
    comment = dialog_manager.dialog_data.get("comment", "")
    return {
        "title": title,
        "amount": amount,
        "comment": comment,
    }


async def get_confirm_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна подтверждения"""
    title = dialog_manager.dialog_data.get("title", "")
    amount = dialog_manager.dialog_data.get("amount", "")
    comment = dialog_manager.dialog_data.get("comment", "")
    invoice_file_id = dialog_manager.dialog_data.get("invoice_file_id")

    return {
        "title": title,
        "amount": amount,
        "comment": comment,
        "invoice_status": "✅ Прикреплен" if invoice_file_id else "❌ Не прикреплен",
    }


async def get_success_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    """Получает данные для окна успешного создания"""
    user = kwargs.get("user")
    payment_request_id = dialog_manager.dialog_data.get("payment_request_id")
    billing_contacts_count = dialog_manager.dialog_data.get("billing_contacts_count", 0)

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, payment_request_id)

        if not payment_request:
            return {"error": "Request not found"}

        # Форматируем полное сообщение о запросе
        request_text = format_payment_request_message(
            request_id=payment_request.id,
            title=payment_request.title,
            amount=payment_request.amount,
            comment=payment_request.comment,
            created_by_name=user.display_name,
            status=payment_request.status,
            created_at=payment_request.created_at,
        )

        return {
            "request_text": request_text,
            "billing_contacts_count": billing_contacts_count,
        }


# ============ Message Input Handlers ============

async def on_title_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода названия"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, отправьте текстовое сообщение"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_title)
        return

    title = message.text.strip()

    if not title:
        manager.dialog_data["error"] = "❌ Название не может быть пустым. Попробуйте еще раз:"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_title)
        return

    if len(title) > 200:
        manager.dialog_data["error"] = "❌ Название слишком длинное (максимум 200 символов). Попробуйте еще раз:"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_title)
        return

    # Успешная валидация - очищаем ошибку и переходим дальше
    manager.dialog_data.pop("error", None)
    manager.dialog_data["title"] = title
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(PaymentRequestCreation.enter_amount)


async def on_amount_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода суммы"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, отправьте текстовое сообщение"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_amount)
        return

    amount = message.text.strip()

    # Валидация: проверяем что это число
    try:
        amount_float = float(amount.replace(",", ".").replace(" ", ""))
        if amount_float <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        manager.dialog_data["error"] = "❌ Некорректная сумма. Введите число больше 0 (например: 5000 или 5000.50):"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_amount)
        return

    # Форматируем сумму для красивого отображения
    if amount_float == int(amount_float):
        # Целое число - без копеек, с пробелами для тысяч
        formatted_amount = f"{int(amount_float):,}".replace(",", " ")
    else:
        # Есть копейки - с двумя знаками после точки, с пробелами для тысяч
        formatted_amount = f"{amount_float:,.2f}".replace(",", " ")

    # Успешная валидация - очищаем ошибку и сохраняем отформатированную сумму
    manager.dialog_data.pop("error", None)
    manager.dialog_data["amount"] = formatted_amount
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(PaymentRequestCreation.enter_comment)


async def on_comment_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода комментария"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, отправьте текстовое сообщение или нажмите кнопку Пропустить"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_comment)
        return

    comment = message.text.strip()

    if len(comment) > 1000:
        manager.dialog_data["error"] = "❌ Комментарий слишком длинный (максимум 1000 символов). Попробуйте еще раз:"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.enter_comment)
        return

    # Успешная валидация - очищаем ошибку и переходим дальше
    manager.dialog_data.pop("error", None)
    manager.dialog_data["comment"] = comment
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(PaymentRequestCreation.attach_invoice)


async def on_invoice_document(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик загрузки документа счета"""
    if message.document:
        # Сохраняем file_id документа
        manager.dialog_data["invoice_file_id"] = message.document.file_id
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.confirm)
    else:
        await message.answer("❌ Пожалуйста, отправьте документ (файл).")


# ============ Button Handlers ============

async def on_skip_comment(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Пропустить комментарий"""
    manager.dialog_data["comment"] = "—"  # Дефолтное значение
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(PaymentRequestCreation.attach_invoice)


async def on_skip_invoice(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Пропустить прикрепление счета"""
    manager.dialog_data["invoice_file_id"] = None
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(PaymentRequestCreation.confirm)


async def on_send_request(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отправка запроса на оплату"""
    user = manager.middleware_data.get("user")
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    title = manager.dialog_data.get("title", "")
    amount = manager.dialog_data.get("amount", "")
    comment = manager.dialog_data.get("comment", "")
    invoice_file_id = manager.dialog_data.get("invoice_file_id")

    try:
        async with get_session() as session:
            # Создаем запрос на оплату
            payment_request = await PaymentRequestCRUD.create_payment_request(
                session=session,
                created_by_id=user.id,
                title=title,
                amount=amount,
                comment=comment,
                invoice_file_id=invoice_file_id,
            )

            logger.info(f"Payment request #{payment_request.id} created by user {user.id}")

            # Получаем billing контакты
            billing_contacts = await UserCRUD.get_billing_contacts(session)

            if not billing_contacts:
                logger.warning("No billing contacts found!")
                await callback.answer(
                    "⚠️ Запрос создан, но billing контакты не найдены. "
                    "Обратитесь к администратору.",
                    show_alert=True
                )
                await manager.done()
                await manager.start(MainMenu.main)
                return

            # Формируем сообщение для billing контактов
            message_text = format_payment_request_message(
                request_id=payment_request.id,
                title=payment_request.title,
                amount=payment_request.amount,
                comment=payment_request.comment,
                created_by_name=user.display_name,
                status=payment_request.status,
                created_at=payment_request.created_at,
            )

            keyboard = get_payment_request_keyboard(payment_request.id, payment_request.status)

            # Отправляем уведомление ВСЕМ billing контактам и сохраняем message_id для каждого
            for billing_contact in billing_contacts:
                if billing_contact.telegram_id:
                    try:
                        # Отправляем сообщение
                        sent_message = await callback.bot.send_message(
                            chat_id=billing_contact.telegram_id,
                            text=message_text,
                            reply_markup=keyboard,
                        )

                        # Если есть счет, отправляем его
                        if invoice_file_id:
                            await callback.bot.send_document(
                                chat_id=billing_contact.telegram_id,
                                document=invoice_file_id,
                                caption=f"📎 Счет к запросу #{payment_request.id}",
                            )

                        # Сохраняем уведомление в базу
                        await BillingNotificationCRUD.create_billing_notification(
                            session=session,
                            payment_request_id=payment_request.id,
                            billing_user_id=billing_contact.id,
                            message_id=sent_message.message_id,
                            chat_id=billing_contact.telegram_id,
                        )

                        logger.info(f"Notification sent to billing contact {billing_contact.telegram_username}")

                    except Exception as e:
                        logger.error(f"Error sending notification to {billing_contact.telegram_username}: {e}", exc_info=True)

            # Сохраняем ID текущего сообщения диалога как worker_message_id
            # (это сообщение будет обновляться при изменении статуса)
            current_message_id = callback.message.message_id

            await PaymentRequestCRUD.set_worker_message_id(
                session=session,
                request_id=payment_request.id,
                message_id=current_message_id,
            )

            # Сохраняем данные для отображения в окне success
            manager.dialog_data["payment_request_id"] = payment_request.id
            manager.dialog_data["billing_contacts_count"] = len(billing_contacts)

        # Переходим на окно успешного создания вместо закрытия диалога
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(PaymentRequestCreation.success)

    except Exception as e:
        logger.error(f"Error creating payment request: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании запроса", show_alert=True)


async def on_cancel_request(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отмена создания запроса"""
    await callback.answer("Создание запроса отменено")
    await manager.done()
    await manager.start(MainMenu.main)


# ============ Dialog Windows ============

# Окно 1: Ввод названия
title_window = Window(
    Const("💰 <b>Создание запроса на оплату</b>\n\n"
          "Шаг 1 из 4: Введите название для плательщика\n\n"
          "Например: <i>Оплата за дизайн логотипа</i>"),
    Format("\n{error}\n", when="error"),
    Cancel(Const("❌ Отмена")),
    MessageInput(on_title_input),
    state=PaymentRequestCreation.enter_title,
    getter=get_title_data,
)

# Окно 2: Ввод суммы
amount_window = Window(
    Format("💰 <b>Создание запроса на оплату</b>\n\n"
           "Название: <i>{title}</i>\n\n"
           "Шаг 2 из 4: Введите сумму в рублях\n\n"
           "Например: <i>5000</i> или <i>5000.50</i>"),
    Format("\n{error}\n", when="error"),
    Cancel(Const("❌ Отмена")),
    MessageInput(on_amount_input),
    state=PaymentRequestCreation.enter_amount,
    getter=get_amount_data,
)

# Окно 3: Ввод комментария
comment_window = Window(
    Format("💰 <b>Создание запроса на оплату</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n\n"
           "Шаг 3 из 4: Введите комментарий к запросу (опционально)\n\n"
           "Например: <i>Аванс 50%, остальное после сдачи проекта</i>\n"
           "Или нажмите <b>Пропустить</b>"),
    Format("\n{error}\n", when="error"),
    Column(
        Button(Const("⏭️ Пропустить"), id="skip_comment", on_click=on_skip_comment),
        Cancel(Const("❌ Отмена")),
    ),
    MessageInput(on_comment_input),
    state=PaymentRequestCreation.enter_comment,
    getter=get_comment_data,
)

# Окно 4: Прикрепление счета
attach_invoice_window = Window(
    Format("💰 <b>Создание запроса на оплату</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n"
           "Комментарий: <i>{comment}</i>\n\n"
           "Шаг 4 из 4: Прикрепите счет (опционально)\n\n"
           "Отправьте документ или нажмите <b>Пропустить</b>"),
    Column(
        Button(Const("⏭️ Пропустить"), id="skip_invoice", on_click=on_skip_invoice),
        Cancel(Const("❌ Отмена")),
    ),
    MessageInput(on_invoice_document, content_types=[ContentType.DOCUMENT]),
    state=PaymentRequestCreation.attach_invoice,
    getter=get_attach_invoice_data,
)

# Окно 5: Подтверждение
confirm_window = Window(
    Format("💰 <b>Подтверждение запроса на оплату</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n"
           "Комментарий: <i>{comment}</i>\n"
           "Счет: {invoice_status}\n\n"
           "Отправить запрос на оплату?"),
    Column(
        Button(Const("✅ Отправить"), id="send_request", on_click=on_send_request),
        Button(Const("❌ Отмена"), id="cancel_request", on_click=on_cancel_request),
    ),
    state=PaymentRequestCreation.confirm,
    getter=get_confirm_data,
)


# Окно 6: Успешное создание запроса
success_window = Window(
    Format("{request_text}"),
    Format("\n📤 Уведомление отправлено {billing_contacts_count} плательщикам"),
    Const("\n✅ <b>Запрос на оплату успешно создан!</b>\n"),
    Const("Это окно будет обновляться при изменении статуса запроса."),
    Button(
        Const("🏠 Главное меню"),
        id="go_to_main_menu",
        on_click=lambda c, b, m: m.start(MainMenu.main),
    ),
    state=PaymentRequestCreation.success,
    getter=get_success_data,
)


# Создаем диалог
payment_request_creation_dialog = Dialog(
    title_window,
    amount_window,
    comment_window,
    attach_invoice_window,
    confirm_window,
    success_window,
)
