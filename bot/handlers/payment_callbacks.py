"""Обработчики callback для платежей (inline кнопки для billing контактов)"""

import logging
from datetime import date, datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import DialogManager, StartMode, ShowMode

from bot.database import get_session, PaymentRequestCRUD, UserCRUD, PaymentRequestStatus, BillingNotificationCRUD
from bot.states import MainMenu

logger = logging.getLogger(__name__)

# Router для callback handlers
payment_callbacks_router = Router()


# FSM для загрузки платежки
class UploadProof(StatesGroup):
    waiting_for_document = State()


# FSM для выбора даты
class SelectDate(StatesGroup):
    waiting_for_date = State()


# FSM для отмены с комментарием
class CancelWithComment(StatesGroup):
    waiting_for_comment = State()


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
            processing_by_id=user.id,  # Устанавливаем кто взял в работу
        )

        if not payment_request:
            await message.answer("❌ Ошибка при обновлении запроса")
            await state.clear()
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
            paid_by_name=user.display_name,
            paid_at=payment_request.paid_at,
        )

        for notification in billing_notifications:
            try:
                await message.bot.edit_message_text(
                    chat_id=notification.chat_id,
                    message_id=notification.message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing notification {notification.id}: {e}")

        # Отправляем НОВОЕ уведомление Worker'у и платежку
        if payment_request.created_by.telegram_id:
            try:
                # Формируем текст уведомления
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

                # Отправляем НОВОЕ уведомление
                await message.bot.send_message(
                    chat_id=payment_request.created_by.telegram_id,
                    text=worker_text,
                )

                # Отправляем платежку отдельным документом с кнопкой "Главное меню"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="worker_payment_goto_main_menu")]
                ])

                await message.bot.send_document(
                    chat_id=payment_request.created_by.telegram_id,
                    document=payment_proof_file_id,
                    caption=f"📎 Платежка к запросу #{payment_request.id}",
                    reply_markup=keyboard,
                )
            except Exception as e:
                logger.error(f"Error notifying worker: {e}")

        # Редактируем сообщение с запросом документа
        upload_proof_message_id = data.get("upload_proof_message_id")
        if upload_proof_message_id:
            try:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="goto_main_menu")]
                ])

                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=upload_proof_message_id,
                    text=(
                        f"✅ Запрос #{request_id} отмечен как оплаченный!\n"
                        f"Worker получит уведомление и платежку."
                    ),
                    reply_markup=keyboard
                )
            except Exception as e:
                logger.error(f"Error editing upload proof message: {e}")
                # Если не удалось отредактировать - отправляем новое
                await message.answer(
                    f"✅ Запрос #{request_id} отмечен как оплаченный!\n"
                    f"Worker получит уведомление и платежку."
                )
        else:
            # Fallback если message_id не был сохранен
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
            processing_by_name=user.display_name,
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
            processing_by_name=user.display_name,
            scheduled_date=scheduled_date,
        )

        for notification in billing_notifications:
            try:
                await message.bot.edit_message_text(
                    chat_id=notification.chat_id,
                    message_id=notification.message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing notification {notification.id}: {e}")

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
async def on_payment_cancel(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Отменить' - запрашивает комментарий"""
    request_id = int(callback.data.split(":")[1])

    # Проверяем что запрос существует
    async with get_session() as session:
        payment_request = await PaymentRequestCRUD.get_payment_request_by_id(session, request_id)

        if not payment_request:
            await callback.answer("❌ Запрос не найден", show_alert=True)
            return

        # Проверяем что запрос еще можно отменить
        if payment_request.status in [PaymentRequestStatus.PAID, PaymentRequestStatus.CANCELLED]:
            await callback.answer("❌ Запрос уже обработан", show_alert=True)
            return

    # Сохраняем request_id в state и запрашиваем комментарий
    await state.set_state(CancelWithComment.waiting_for_comment)

    # Отправляем сообщение и сохраняем его message_id в state
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


@payment_callbacks_router.callback_query(F.data.startswith("pay_cancel_schedule:"))
async def on_cancel_schedule_selection(callback: CallbackQuery):
    """Обработчик отмены выбора даты"""
    await callback.message.delete()
    await callback.answer("Выбор даты отменен")


@payment_callbacks_router.callback_query(F.data.startswith("cancel_action:"))
async def on_cancel_action(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки 'Отменить действие' при вводе комментария отмены"""
    await state.clear()
    await callback.message.delete()
    await callback.answer("Действие отменено")


@payment_callbacks_router.callback_query(F.data == "cancel_goto_main_menu")
async def on_cancel_goto_main_menu(callback: CallbackQuery, dialog_manager: DialogManager):
    """Обработчик кнопки 'Главное меню' после отмены запроса"""
    # Удаляем кнопку из сообщения (оставляем только текст)
    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error removing button: {e}")

    await callback.answer()

    # Закрываем текущий диалог если есть
    if dialog_manager.has_context():
        await dialog_manager.done()

    # Запускаем главное меню
    await dialog_manager.start(MainMenu.main, mode=StartMode.RESET_STACK)


@payment_callbacks_router.callback_query(F.data == "worker_payment_goto_main_menu")
async def on_worker_payment_goto_main_menu(callback: CallbackQuery, dialog_manager: DialogManager):
    """Обработчик кнопки 'Главное меню' на документе платежки для Worker'а"""
    # Удаляем кнопку из сообщения с документом
    try:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Error removing button from payment document: {e}")

    await callback.answer()

    # Закрываем все текущие диалоги
    if dialog_manager.has_context():
        await dialog_manager.done()

    # Запускаем главное меню с явным указанием ОТПРАВИТЬ новое сообщение
    await dialog_manager.start(
        MainMenu.main,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.SEND  # ← Ключевой параметр: отправить НОВОЕ сообщение
    )


@payment_callbacks_router.message(CancelWithComment.waiting_for_comment)
async def on_cancel_comment_received(message: Message, state: FSMContext, **kwargs):
    """Обработчик получения комментария для отмены запроса"""
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение с причиной отмены.")
        return

    # Получаем user из middleware_data
    user = kwargs.get("user")

    cancel_comment = message.text.strip()
    data = await state.get_data()
    request_id = data.get("request_id")
    cancel_request_message_id = data.get("cancel_request_message_id")

    if not request_id:
        await message.answer("❌ Ошибка: ID запроса не найден")
        await state.clear()
        return

    async with get_session() as session:
        # Отменяем запрос
        payment_request = await PaymentRequestCRUD.cancel_payment_request(session, request_id)

        if not payment_request:
            await message.answer("❌ Ошибка при отмене запроса")
            await state.clear()
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
                await message.bot.edit_message_text(
                    chat_id=notification.chat_id,
                    message_id=notification.message_id,
                    text=new_text,
                    reply_markup=get_payment_request_keyboard(payment_request.id, payment_request.status),
                )
            except Exception as e:
                logger.error(f"Error updating billing notification {notification.id}: {e}")

        # Отправляем НОВОЕ уведомление Worker (не редактируем)
        if payment_request.created_by.telegram_id:
            try:
                worker_notification = (
                    f"❌ <b>Запрос на оплату #{payment_request.id} отменен</b>\n\n"
                    f"<b>Название:</b> {payment_request.title}\n"
                    f"<b>Сумма:</b> {payment_request.amount} ₽\n\n"
                    f"<b>Причина отмены:</b> {cancel_comment}\n"
                    f"<b>Отменил:</b> {user.display_name if user else 'Billing контакт'}"
                )

                # Кнопка в главное меню
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="goto_main_menu")]
                ])

                await message.bot.send_message(
                    chat_id=payment_request.created_by.telegram_id,
                    text=worker_notification,
                    reply_markup=keyboard,
                )
            except Exception as e:
                logger.error(f"Error notifying worker: {e}")

        # Редактируем сообщение с запросом комментария
        if cancel_request_message_id:
            try:
                confirmation_text = (
                    f"✅ <b>Запрос #{request_id} отменен</b>\n\n"
                    f"<b>Причина отмены:</b> {cancel_comment}\n\n"
                    f"Сотрудник получил уведомление с причиной отмены."
                )

                # Добавляем кнопку "Главное меню"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🏠 Главное меню", callback_data="cancel_goto_main_menu")]
                ])

                await message.bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=cancel_request_message_id,
                    text=confirmation_text,
                    reply_markup=keyboard,
                )

                # Удаляем сообщение пользователя с комментарием для чистоты чата
                try:
                    await message.delete()
                except Exception:
                    pass  # Не критично если не удалось удалить

            except Exception as e:
                logger.error(f"Error editing cancel request message: {e}")
                # Если не удалось отредактировать - отправляем новое
                await message.answer(
                    f"✅ Запрос #{request_id} отменен!\n"
                    f"Worker получил уведомление с причиной отмены."
                )

    await state.clear()
