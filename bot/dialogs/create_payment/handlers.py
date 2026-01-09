"""Handlers для диалога создания платежа"""

import logging
from datetime import datetime
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.kbd import Button, Select
from aiogram_dialog.widgets.input import MessageInput

from .states import CreatePayment
from bot.dialogs.payments_menu.states import PaymentsMenu
from bot.database import get_session, PaymentRequestCRUD
from bot.database.models import PaymentRequestStatus

logger = logging.getLogger(__name__)


# ============ Message Input Handlers ============

async def on_title_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода названия"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, отправьте текстовое сообщение"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_title)
        return

    title = message.text.strip()

    if not title:
        manager.dialog_data["error"] = "❌ Название не может быть пустым"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_title)
        return

    if len(title) > 200:
        manager.dialog_data["error"] = "❌ Название слишком длинное (максимум 200 символов)"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_title)
        return

    manager.dialog_data.pop("error", None)
    manager.dialog_data["title"] = title
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.enter_amount)


async def on_amount_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода суммы"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, отправьте текстовое сообщение"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_amount)
        return

    amount = message.text.strip()

    try:
        amount_float = float(amount.replace(",", ".").replace(" ", ""))
        if amount_float <= 0:
            raise ValueError("Amount must be positive")
    except ValueError:
        manager.dialog_data["error"] = "❌ Некорректная сумма. Введите число больше 0"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_amount)
        return

    # Форматируем сумму
    if amount_float == int(amount_float):
        formatted_amount = f"{int(amount_float):,}".replace(",", " ")
    else:
        formatted_amount = f"{amount_float:,.2f}".replace(",", " ")

    manager.dialog_data.pop("error", None)
    manager.dialog_data["amount"] = formatted_amount
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.enter_comment)


async def on_comment_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода комментария"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, отправьте текст или нажмите Пропустить"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_comment)
        return

    comment = message.text.strip()

    if len(comment) > 1000:
        manager.dialog_data["error"] = "❌ Комментарий слишком длинный (максимум 1000 символов)"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_comment)
        return

    manager.dialog_data.pop("error", None)
    manager.dialog_data["comment"] = comment
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.select_status)


async def on_scheduled_date_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода даты планирования"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, введите дату"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_scheduled_date)
        return

    date_str = message.text.strip()

    try:
        # Пробуем различные форматы даты
        for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                break
            except ValueError:
                continue
        else:
            raise ValueError("Invalid date format")

    except ValueError:
        manager.dialog_data["error"] = "❌ Некорректный формат даты. Используйте ДД.ММ.ГГГГ"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_scheduled_date)
        return

    manager.dialog_data.pop("error", None)
    manager.dialog_data["scheduled_date"] = parsed_date.strftime("%d.%m.%Y")
    manager.dialog_data["scheduled_date_obj"] = parsed_date
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.attach_invoice)


async def on_paid_date_input(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик ввода даты оплаты"""
    if not message.text:
        manager.dialog_data["error"] = "❌ Пожалуйста, введите дату"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_paid_date)
        return

    date_str = message.text.strip()

    try:
        for fmt in ["%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError("Invalid date format")

    except ValueError:
        manager.dialog_data["error"] = "❌ Некорректный формат даты. Используйте ДД.ММ.ГГГГ"
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_paid_date)
        return

    manager.dialog_data.pop("error", None)
    manager.dialog_data["paid_date"] = parsed_date.strftime("%d.%m.%Y")
    manager.dialog_data["paid_date_obj"] = parsed_date
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.attach_invoice)


async def on_invoice_document(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик загрузки счета"""
    if message.document:
        manager.dialog_data["invoice_file_id"] = message.document.file_id
        status = manager.dialog_data.get("status", "pending")

        if status == "paid":
            # Для оплаченных - переходим к загрузке платежки
            manager.show_mode = ShowMode.EDIT
            await manager.switch_to(CreatePayment.attach_payment_proof)
        else:
            # Для остальных - к подтверждению
            manager.show_mode = ShowMode.EDIT
            await manager.switch_to(CreatePayment.confirm)
    else:
        await message.answer("❌ Пожалуйста, отправьте документ (файл)")


async def on_payment_proof_document(message: Message, widget: MessageInput, manager: DialogManager):
    """Обработчик загрузки платежки"""
    if message.document:
        manager.dialog_data["payment_proof_file_id"] = message.document.file_id
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.confirm)
    else:
        await message.answer("❌ Пожалуйста, отправьте документ (файл)")


# ============ Button Handlers ============

async def on_skip_comment(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Пропустить комментарий"""
    manager.dialog_data["comment"] = "—"
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.select_status)


async def on_status_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    """Обработка выбора статуса"""
    manager.dialog_data["status"] = item_id

    if item_id == "scheduled":
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_scheduled_date)
    elif item_id == "paid":
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.enter_paid_date)
    else:  # pending
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.attach_invoice)


async def on_use_today_date(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Использовать сегодняшнюю дату"""
    today = datetime.now().date()
    status = manager.dialog_data.get("status")

    if status == "scheduled":
        manager.dialog_data["scheduled_date"] = today.strftime("%d.%m.%Y")
        manager.dialog_data["scheduled_date_obj"] = today
    elif status == "paid":
        manager.dialog_data["paid_date"] = today.strftime("%d.%m.%Y")
        manager.dialog_data["paid_date_obj"] = datetime.now()

    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.attach_invoice)


async def on_skip_invoice(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Пропустить прикрепление счета"""
    manager.dialog_data["invoice_file_id"] = None
    status = manager.dialog_data.get("status", "pending")

    if status == "paid":
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.attach_payment_proof)
    else:
        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.confirm)


async def on_skip_payment_proof(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Пропустить прикрепление платежки"""
    manager.dialog_data["payment_proof_file_id"] = None
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(CreatePayment.confirm)


async def on_create_payment(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Создание платежа"""
    user = manager.middleware_data.get("user")
    if not user:
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    title = manager.dialog_data.get("title", "")
    amount = manager.dialog_data.get("amount", "")
    comment = manager.dialog_data.get("comment", "—")
    status_str = manager.dialog_data.get("status", "pending")
    invoice_file_id = manager.dialog_data.get("invoice_file_id")
    payment_proof_file_id = manager.dialog_data.get("payment_proof_file_id")
    scheduled_date_obj = manager.dialog_data.get("scheduled_date_obj")
    paid_date_obj = manager.dialog_data.get("paid_date_obj")

    # Определяем статус
    status_map = {
        "pending": PaymentRequestStatus.PENDING,
        "scheduled": PaymentRequestStatus.SCHEDULED_DATE,
        "paid": PaymentRequestStatus.PAID,
    }
    status = status_map.get(status_str, PaymentRequestStatus.PENDING)

    try:
        async with get_session() as session:
            payment_request = await PaymentRequestCRUD.create_payment_request(
                session=session,
                created_by_id=user.id,
                title=title,
                amount=amount,
                comment=comment,
                invoice_file_id=invoice_file_id,
                payment_proof_file_id=payment_proof_file_id,
                status=status,
                paid_at=paid_date_obj if status == PaymentRequestStatus.PAID else None,
                paid_by_id=user.id if status == PaymentRequestStatus.PAID else None,
                scheduled_date=scheduled_date_obj if status == PaymentRequestStatus.SCHEDULED_DATE else None,
            )

            logger.info(f"Payment #{payment_request.id} created by {user.telegram_username} with status {status.value}")

            manager.dialog_data["payment_id"] = payment_request.id

        manager.show_mode = ShowMode.EDIT
        await manager.switch_to(CreatePayment.success)

    except Exception as e:
        logger.error(f"Error creating payment: {e}", exc_info=True)
        await callback.answer("❌ Ошибка при создании платежа", show_alert=True)


async def on_cancel(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Отмена создания платежа"""
    await callback.answer("Создание платежа отменено")
    await manager.done()
    await manager.start(PaymentsMenu.main)


async def on_back_to_payments_menu(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Возврат в меню платежей"""
    await manager.done()
    await manager.start(PaymentsMenu.main)
