"""Обработчики callback для платежей (inline кнопки для billing контактов)"""

import logging
from datetime import date, datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.database import get_session, PaymentRequestCRUD, UserCRUD, PaymentRequestStatus

logger = logging.getLogger(__name__)

# Router для callback handlers
payment_callbacks_router = Router()


# FSM для загрузки платежки
class UploadProof(StatesGroup):
    waiting_for_document = State()


# FSM для выбора даты
class SelectDate(StatesGroup):
    waiting_for_date = State()


def get_payment_request_keyboard(request_id: int, status: PaymentRequestStatus) -> InlineKeyboardMarkup:
    """Генерирует клавиатуру для запроса на оплату в зависимости от статуса

    Args:
        request_id: ID запроса на оплату
        status: Текущий статус запроса

    Returns:
        InlineKeyboardMarkup с кнопками действий
    """
    buttons = []

    if status == PaymentRequestStatus.PENDING:
        # Запрос еще никто не взял в работу
        buttons = [
            [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"pay_paid:{request_id}")],
            [InlineKeyboardButton(text="📅 Запланировать", callback_data=f"pay_schedule:{request_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"pay_cancel:{request_id}")],
        ]
    elif status == PaymentRequestStatus.SCHEDULED_TODAY:
        # Запланировано на сегодня
        buttons = [
            [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"pay_paid:{request_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"pay_cancel:{request_id}")],
        ]
    elif status == PaymentRequestStatus.SCHEDULED_DATE:
        # Запланировано на конкретную дату
        buttons = [
            [InlineKeyboardButton(text="✅ Оплачено", callback_data=f"pay_paid:{request_id}")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"pay_cancel:{request_id}")],
        ]
    elif status == PaymentRequestStatus.PAID:
        # Оплачено - кнопок нет
        buttons = []
    elif status == PaymentRequestStatus.CANCELLED:
        # Отменено - кнопок нет
        buttons = []

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def format_payment_request_message(
    request_id: int,
    title: str,
    amount: str,
    comment: str,
    created_by_name: str,
    status: PaymentRequestStatus,
    created_at: datetime,
    processing_by_name: str = None,
    scheduled_date: date = None,
    paid_by_name: str = None,
    paid_at: datetime = None,
) -> str:
    """Форматирует сообщение с деталями запроса на оплату

    Args:
        request_id: ID запроса
        title: Название для плательщика
        amount: Сумма
        comment: Комментарий
        created_by_name: ФИО создателя
        status: Статус запроса
        created_at: Дата создания
        processing_by_name: ФИО взявшего в работу (опционально)
        scheduled_date: Запланированная дата (опционально)
        paid_by_name: ФИО оплатившего (опционально)
        paid_at: Дата оплаты (опционально)

    Returns:
        Форматированное сообщение
    """
    # Статус эмодзи
    status_emoji = {
        PaymentRequestStatus.PENDING: "⏳",
        PaymentRequestStatus.SCHEDULED_TODAY: "📅",
        PaymentRequestStatus.SCHEDULED_DATE: "📅",
        PaymentRequestStatus.PAID: "✅",
        PaymentRequestStatus.CANCELLED: "❌",
    }

    # Статус текст
    status_text = {
        PaymentRequestStatus.PENDING: "Ожидает оплаты",
        PaymentRequestStatus.SCHEDULED_TODAY: "Оплачу сегодня",
        PaymentRequestStatus.SCHEDULED_DATE: f"Запланировано на {scheduled_date.strftime('%d.%m.%Y') if scheduled_date else '?'}",
        PaymentRequestStatus.PAID: f"Оплачено {paid_at.strftime('%d.%m.%Y %H:%M') if paid_at else ''}",
        PaymentRequestStatus.CANCELLED: "Отменено",
    }

    message = (
        f"{status_emoji.get(status, '❓')} <b>Запрос на оплату #{request_id}</b>\n\n"
        f"<b>Статус:</b> {status_text.get(status, 'Неизвестно')}\n"
        f"<b>Название:</b> {title}\n"
        f"<b>Сумма:</b> {amount} ₽\n"
        f"<b>Комментарий:</b> {comment}\n\n"
        f"<b>Создал:</b> {created_by_name}\n"
        f"<b>Дата создания:</b> {created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    if processing_by_name:
        message += f"<b>Взял в работу:</b> {processing_by_name}\n"

    if paid_by_name:
        message += f"<b>Оплатил:</b> {paid_by_name}\n"

    return message


@payment_callbacks_router.callback_query(F.data.startswith("pay_paid:"))
async def on_payment_paid(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Оплачено' - запрашивает загрузку платежки"""
    request_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос еще не оплачен и не отменен
        if payment_request.status in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

    # Сохраняем request_id в FSM state
    await state.set_state(UploadProof.waiting_for_document)
    await state.update_data(request_id=request_id)

    await callback.message.answer(
        "📎 <b>Загрузка подтверждения оплаты</b>\n\n"
        "Пожалуйста, отправьте документ с платежкой (скриншот или PDF).\n\n"
        "Для отмены отправьте /cancel"
    )
    await callback.answer()


@payment_callbacks_router.message(UploadProof.waiting_for_document, F.document)
async def on_proof_document(message: Message, state: FSMContext):
    """Обработчик загрузки документа платежки"""
    data = await state.get_data()
    request_id = data.get("request_id")

    if not request_id:
        await message.answer("❌ Ошибка: ID запроса не найден")
        await state.clear()
        return

    # Получаем file_id документа
    payment_proof_file_id = message.document.file_id

    async with get_session() as session:
        # Получаем telegram_id billing контакта
        from bot.database import UserCRUD
        user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id)

        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return

        # Отмечаем запрос как оплаченный
        payment_request = await PaymentRequestCRUD.mark_as_paid(
            session=session,
            request_id=request_id,
            paid_by_id=user.id,
            payment_proof_file_id=payment_proof_file_id,
        )

        if not payment_request:
            await message.answer("❌ Ошибка при обновлении запроса")
            await state.clear()
            return

        # Обновляем сообщение у billing контакта
        if payment_request.billing_message_id:
            try:
                new_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                    paid_by_name=user.display_name,
                    paid_at=payment_request.paid_at,
                )

                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=payment_request.billing_message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing message: {e}")

        # Обновляем сообщение Worker и отправляем платежку отдельно
        if payment_request.worker_message_id and payment_request.created_by.telegram_id:
            try:
                # Обновляем основное сообщение Worker
                worker_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                    paid_by_name=user.display_name,
                    paid_at=payment_request.paid_at,
                )
                worker_text += "\n\n📎 Платежка отправлена отдельным сообщением ⬇️"

                await message.bot.edit_message_text(
                    chat_id=payment_request.created_by.telegram_id,
                    message_id=payment_request.worker_message_id,
                    text=worker_text,
                )

                # Отправляем платежку отдельным документом
                await message.bot.send_document(
                    chat_id=payment_request.created_by.telegram_id,
                    document=payment_proof_file_id,
                    caption=f"📎 Платежка к запросу #{payment_request.id}",
                )
            except Exception as e:
                logger.error(f"Error notifying worker: {e}")

        await message.answer(
            f"✅ Запрос #{request_id} отмечен как оплаченный!\n"
            f"Worker получит уведомление и платежку."
        )

    await state.clear()


@payment_callbacks_router.message(UploadProof.waiting_for_document, F.photo)
async def on_proof_photo(message: Message, state: FSMContext):
    """Обработчик загрузки фото платежки (преобразуем в document)"""
    await message.answer(
        "⚠️ Пожалуйста, отправьте изображение как <b>документ</b>, а не как фото.\n"
        "Это сохранит качество изображения.\n\n"
        "В Telegram: нажмите на скрепку → Файл → выберите изображение"
    )


@payment_callbacks_router.callback_query(F.data.startswith("pay_schedule:"))
async def on_payment_schedule(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Запланировать' - выбор даты"""
    request_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос еще не обработан
        if payment_request.status in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

    # Создаем клавиатуру для выбора даты
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data=f"pay_today:{request_id}")],
        [InlineKeyboardButton(text="📆 Выбрать дату", callback_data=f"pay_date:{request_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data=f"pay_cancel_schedule:{request_id}")],
    ])

    await callback.message.answer(
        "📅 <b>Планирование оплаты</b>\n\n"
        "Когда планируете оплатить?",
        reply_markup=keyboard,
    )
    await callback.answer()


@payment_callbacks_router.callback_query(F.data.startswith("pay_today:"))
async def on_payment_schedule_today(callback: CallbackQuery):
    """Обработчик 'Оплачу сегодня'"""
    request_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        # Получаем пользователя
        user = await UserCRUD.get_user_by_telegram_id(session, callback.from_user.id)

        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return

        # Планируем на сегодня
        payment_request = await PaymentRequestCRUD.schedule_payment(
            session=session,
            request_id=request_id,
            processing_by_id=user.id,
            is_today=True,
        )

        if not payment_request:
            await callback.answer("❌ Ошибка при обновлении запроса", show_alert=True)
            return

        # Обновляем сообщение
        if payment_request.billing_message_id:
            try:
                new_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                    processing_by_name=user.display_name,
                )

                await callback.bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=payment_request.billing_message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing message: {e}")

        # Обновляем сообщение Worker (вместо создания нового)
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
                    processing_by_name=user.display_name,
                )

                await callback.bot.edit_message_text(
                    chat_id=payment_request.created_by.telegram_id,
                    message_id=payment_request.worker_message_id,
                    text=worker_text,
                )
            except Exception as e:
                logger.error(f"Error updating worker message: {e}")

    await callback.answer(
        f"✅ Запрос #{request_id} запланирован на сегодня!\nВы получите напоминание в 18:00 МСК.",
        show_alert=True
    )


@payment_callbacks_router.callback_query(F.data.startswith("pay_date:"))
async def on_payment_schedule_date(callback: CallbackQuery, state: FSMContext):
    """Обработчик 'Выбрать дату' - запрашивает ввод даты"""
    request_id = int(callback.data.split(":")[1])

    await state.set_state(SelectDate.waiting_for_date)
    await state.update_data(request_id=request_id)

    await callback.message.answer(
        "📆 <b>Выбор даты оплаты</b>\n\n"
        "Введите дату в формате <code>ДД.ММ.ГГГГ</code>\n"
        "Например: <code>25.12.2025</code>\n\n"
        "Для отмены отправьте /cancel"
    )
    await callback.answer()


@payment_callbacks_router.message(SelectDate.waiting_for_date, F.text)
async def on_date_input(message: Message, state: FSMContext):
    """Обработчик ввода даты"""
    data = await state.get_data()
    request_id = data.get("request_id")

    if not request_id:
        await message.answer("❌ Ошибка: ID запроса не найден")
        await state.clear()
        return

    # Парсим дату
    try:
        scheduled_date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()

        # Проверяем что дата в будущем
        if scheduled_date < date.today():
            await message.answer("❌ Дата не может быть в прошлом. Попробуйте еще раз:")
            return

    except ValueError:
        await message.answer(
            "❌ Некорректный формат даты.\n"
            "Используйте формат <code>ДД.ММ.ГГГГ</code>\n"
            "Например: <code>25.12.2025</code>"
        )
        return

    async with get_session() as session:
        # Получаем пользователя
        user = await UserCRUD.get_user_by_telegram_id(session, message.from_user.id)

        if not user:
            await message.answer("❌ Пользователь не найден")
            await state.clear()
            return

        # Планируем на дату
        payment_request = await PaymentRequestCRUD.schedule_payment(
            session=session,
            request_id=request_id,
            processing_by_id=user.id,
            scheduled_date=scheduled_date,
            is_today=False,
        )

        if not payment_request:
            await message.answer("❌ Ошибка при обновлении запроса")
            await state.clear()
            return

        # Обновляем сообщение у billing контакта
        if payment_request.billing_message_id:
            try:
                new_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                    processing_by_name=user.display_name,
                    scheduled_date=scheduled_date,
                )

                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=payment_request.billing_message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing message: {e}")

        # Обновляем сообщение Worker (вместо создания нового)
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
                    processing_by_name=user.display_name,
                    scheduled_date=scheduled_date,
                )

                await message.bot.edit_message_text(
                    chat_id=payment_request.created_by.telegram_id,
                    message_id=payment_request.worker_message_id,
                    text=worker_text,
                )
            except Exception as e:
                logger.error(f"Error updating worker message: {e}")

        await message.answer(
            f"✅ Запрос #{request_id} запланирован на {scheduled_date.strftime('%d.%m.%Y')}!\n"
            f"Вы получите напоминание в 10:00 МСК в день оплаты."
        )

    await state.clear()


@payment_callbacks_router.callback_query(F.data.startswith("pay_cancel:"))
async def on_payment_cancel(callback: CallbackQuery):
    """Обработчик кнопки 'Отменить'"""
    request_id = int(callback.data.split(":")[1])

    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.cancel_payment_request(session, request_id)

        if not payment_request:
            await callback.answer("❌ Ошибка при отмене запроса", show_alert=True)
            return

        # Обновляем сообщение у billing контакта
        if payment_request.billing_message_id:
            try:
                new_text = format_payment_request_message(
                    request_id=payment_request.id,
                    title=payment_request.title,
                    amount=payment_request.amount,
                    comment=payment_request.comment,
                    created_by_name=payment_request.created_by.display_name,
                    status=payment_request.status,
                    created_at=payment_request.created_at,
                )

                await callback.bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=payment_request.billing_message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing message: {e}")

        # Обновляем сообщение Worker (вместо создания нового)
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


@payment_callbacks_router.callback_query(F.data.startswith("pay_cancel_schedule:"))
async def on_cancel_schedule_selection(callback: CallbackQuery):
    """Обработчик отмены выбора даты"""
    await callback.message.delete()
    await callback.answer("Выбор даты отменен")
