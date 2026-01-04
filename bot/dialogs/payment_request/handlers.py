"""Handlers для диалога создания запроса на оплату"""

import logging
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button
from aiogram_dialog.widgets.input import MessageInput

from bot.states import PaymentRequestCreation, MainMenu
from bot.database import get_session, PaymentRequestCRUD, UserCRUD, BillingNotificationCRUD
from bot.handlers.payment_callbacks import format_payment_request_message, get_payment_request_keyboard

logger = logging.getLogger(__name__)


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
