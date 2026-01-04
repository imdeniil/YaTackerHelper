"""Window definitions для диалога создания запроса на оплату"""

from aiogram.types import ContentType
from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Cancel, Column
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from bot.states import PaymentRequestCreation, MainMenu
from .getters import (
    get_title_data,
    get_amount_data,
    get_comment_data,
    get_attach_invoice_data,
    get_confirm_data,
    get_success_data,
)
from .handlers import (
    on_title_input,
    on_amount_input,
    on_comment_input,
    on_invoice_document,
    on_skip_comment,
    on_skip_invoice,
    on_send_request,
    on_cancel_request,
)


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
