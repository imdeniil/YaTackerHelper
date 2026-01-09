"""Window definitions для диалога создания платежа"""

from aiogram.types import ContentType
from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Column, Select, Group
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from .states import CreatePayment
from .getters import (
    get_title_data,
    get_amount_data,
    get_comment_data,
    get_status_data,
    get_scheduled_date_data,
    get_paid_date_data,
    get_invoice_data,
    get_payment_proof_data,
    get_confirm_data,
    get_success_data,
)
from .handlers import (
    on_title_input,
    on_amount_input,
    on_comment_input,
    on_scheduled_date_input,
    on_paid_date_input,
    on_invoice_document,
    on_payment_proof_document,
    on_skip_comment,
    on_status_selected,
    on_use_today_date,
    on_skip_invoice,
    on_skip_payment_proof,
    on_create_payment,
    on_cancel,
    on_back_to_payments_menu,
)


# Окно 1: Ввод названия
title_window = Window(
    Const("💳 <b>Добавление платежа</b>\n\n"
          "Шаг 1: Введите название платежа\n\n"
          "Например: <i>Оплата за дизайн логотипа</i>"),
    Format("\n{error}\n", when="error"),
    Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    MessageInput(on_title_input),
    state=CreatePayment.enter_title,
    getter=get_title_data,
)


# Окно 2: Ввод суммы
amount_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n\n"
           "Шаг 2: Введите сумму в рублях\n\n"
           "Например: <i>5000</i> или <i>5000.50</i>"),
    Format("\n{error}\n", when="error"),
    Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    MessageInput(on_amount_input),
    state=CreatePayment.enter_amount,
    getter=get_amount_data,
)


# Окно 3: Ввод комментария
comment_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n\n"
           "Шаг 3: Введите комментарий (опционально)\n\n"
           "Или нажмите <b>Пропустить</b>"),
    Format("\n{error}\n", when="error"),
    Column(
        Button(Const("⏭️ Пропустить"), id="skip_comment", on_click=on_skip_comment),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    MessageInput(on_comment_input),
    state=CreatePayment.enter_comment,
    getter=get_comment_data,
)


# Окно 4: Выбор статуса
status_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n"
           "Комментарий: <i>{comment}</i>\n\n"
           "Шаг 4: Выберите статус платежа"),
    Column(
        Select(
            Format("{item[1]}"),
            id="status_select",
            item_id_getter=lambda item: item[0],
            items=[
                ("pending", "⏳ Ожидает оплаты"),
                ("scheduled", "📅 Запланировать"),
                ("paid", "✅ Уже оплачен"),
            ],
            on_click=on_status_selected,
        ),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    state=CreatePayment.select_status,
    getter=get_status_data,
)


# Окно 5a: Выбор даты планирования
scheduled_date_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n\n"
           "📅 Введите дату планирования (ДД.ММ.ГГГГ)\n\n"
           "Или нажмите <b>Сегодня</b>"),
    Format("\n{error}\n", when="error"),
    Column(
        Button(Const("📆 Сегодня"), id="today", on_click=on_use_today_date),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    MessageInput(on_scheduled_date_input),
    state=CreatePayment.enter_scheduled_date,
    getter=get_scheduled_date_data,
)


# Окно 5b: Выбор даты оплаты
paid_date_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n\n"
           "✅ Введите дату оплаты (ДД.ММ.ГГГГ)\n\n"
           "Или нажмите <b>Сегодня</b>"),
    Format("\n{error}\n", when="error"),
    Column(
        Button(Const("📆 Сегодня"), id="today", on_click=on_use_today_date),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    MessageInput(on_paid_date_input),
    state=CreatePayment.enter_paid_date,
    getter=get_paid_date_data,
)


# Окно 6: Прикрепление счета
invoice_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n\n"
           "📎 Прикрепите счет (опционально)\n\n"
           "Отправьте документ или нажмите <b>Пропустить</b>"),
    Column(
        Button(Const("⏭️ Пропустить"), id="skip_invoice", on_click=on_skip_invoice),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    MessageInput(on_invoice_document, content_types=[ContentType.DOCUMENT]),
    state=CreatePayment.attach_invoice,
    getter=get_invoice_data,
)


# Окно 7: Прикрепление платежки (только для PAID)
payment_proof_window = Window(
    Format("💳 <b>Добавление платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n"
           "Дата оплаты: <b>{paid_date}</b>\n\n"
           "💳 Прикрепите платежку (опционально)\n\n"
           "Отправьте документ или нажмите <b>Пропустить</b>"),
    Column(
        Button(Const("⏭️ Пропустить"), id="skip_payment_proof", on_click=on_skip_payment_proof),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    MessageInput(on_payment_proof_document, content_types=[ContentType.DOCUMENT]),
    state=CreatePayment.attach_payment_proof,
    getter=get_payment_proof_data,
)


# Окно 8: Подтверждение
confirm_window = Window(
    Format("💳 <b>Подтверждение платежа</b>\n\n"
           "Название: <i>{title}</i>\n"
           "Сумма: <b>{amount} ₽</b>\n"
           "Комментарий: <i>{comment}</i>\n"
           "Статус: <b>{status_display}</b>\n"),
    Format("Дата планирования: <b>{scheduled_date}</b>\n", when="is_scheduled"),
    Format("Дата оплаты: <b>{paid_date}</b>\n", when="is_paid"),
    Format("Счет: {invoice_status}\n"),
    Format("Платежка: {payment_proof_status}\n", when="is_paid"),
    Const("\nСоздать платеж?"),
    Column(
        Button(Const("✅ Создать"), id="create", on_click=on_create_payment),
        Button(Const("❌ Отмена"), id="cancel", on_click=on_cancel),
    ),
    state=CreatePayment.confirm,
    getter=get_confirm_data,
)


# Окно 9: Успешное создание
success_window = Window(
    Format("✅ <b>Платеж #{payment_id} успешно создан!</b>"),
    Button(
        Const("◀️ В меню платежей"),
        id="back_to_menu",
        on_click=on_back_to_payments_menu,
    ),
    state=CreatePayment.success,
    getter=get_success_data,
)
