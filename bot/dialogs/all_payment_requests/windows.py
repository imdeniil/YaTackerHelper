"""Window definitions для диалога просмотра всех запросов на оплату"""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select, Row
from aiogram_dialog.widgets.text import Const, Format

from bot.states import AllPaymentRequests
from .getters import get_all_requests_list_data, get_all_request_details_data
from .handlers import (
    on_filter_active,
    on_filter_completed,
    on_filter_cancelled,
    on_all_request_selected,
    on_download_invoice_billing,
    on_download_proof_billing,
    on_pay_early,
    on_cancel_early,
    on_pay_now,
    on_schedule_now,
    on_cancel_now,
    on_schedule_today,
    on_select_custom_date,
    on_back_from_schedule,
    on_back_to_all_list,
)


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
