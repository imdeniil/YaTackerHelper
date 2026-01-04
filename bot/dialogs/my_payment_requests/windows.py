"""Window definitions для диалога просмотра своих запросов на оплату"""

from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Cancel, ScrollingGroup, Select, Row
from aiogram_dialog.widgets.text import Const, Format

from bot.states import MyPaymentRequests
from .getters import get_my_requests_list_data, get_request_details_data
from .handlers import (
    on_filter_active,
    on_filter_completed,
    on_filter_cancelled,
    on_request_selected,
    on_download_invoice,
    on_download_proof,
    on_cancel_request,
    on_back_to_list,
)


# Окно 1: Список запросов
list_window = Window(
    Const("💰 <b>Мои запросы на оплату</b>\n"),
    Format("Всего запросов: {total_count}\nПоказано: {count}", when="count"),
    Const(
        "\n<i>Статусы:</i>\n⏳ Ожидает\n📅 Запланировано\n✅ Оплачено\n❌ Отменено\n-----------------------------------------------",
        when="count"
    ),
    Const("\nУ вас пока нет запросов на оплату.", when=lambda data, widget, manager: data.get("count", 0) == 0),

    # Список запросов
    ScrollingGroup(
        Select(
            Format("{item[status_emoji]} #{item[id]} | {item[amount]} | {item[title]}"),
            id="request_select",
            item_id_getter=lambda x: str(x["id"]),
            items="requests",
            on_click=on_request_selected,
        ),
        id="requests_scroll",
        width=1,
        height=6,
        when="count",
    ),

    # Фильтры (показываем только 2 кнопки для других фильтров)
    Row(
        Button(
            Const("✅ Завершенные"),
            id="filter_completed",
            on_click=on_filter_completed,
            when=lambda data, widget, manager: data.get("current_filter") != "completed",
        ),
        Button(
            Const("❌ Отмененные"),
            id="filter_cancelled",
            on_click=on_filter_cancelled,
            when=lambda data, widget, manager: data.get("current_filter") != "cancelled",
        ),
        Button(
            Const("📋 Активные"),
            id="filter_active",
            on_click=on_filter_active,
            when=lambda data, widget, manager: data.get("current_filter") != "active",
        ),
        when="count",
    ),

    Cancel(Const("🏠 Главное меню")),
    state=MyPaymentRequests.list,
    getter=get_my_requests_list_data,
)

# Окно 2: Детали запроса
details_window = Window(
    Format(
        "💰 <b>Запрос на оплату #{id}</b>\n\n"
        "<b>Статус:</b> {status}\n"
        "<b>Название:</b> {title}\n"
        "<b>Сумма:</b> {amount} ₽\n"
        "<b>Комментарий:</b> {comment}\n\n"
        "<b>Дата создания:</b> {created_at}\n"
    ),
    Format("<b>Взял в работу:</b> {processing_by}\n", when="processing_by"),
    Format("<b>Оплатил:</b> {paid_by}\n<b>Дата оплаты:</b> {paid_at}\n", when="paid_by"),
    Format("\n📎 Счет: {invoice_status}"),
    Format("\n📎 Платежка: {payment_proof_status}"),

    Button(
        Const("📥 Скачать счет"),
        id="download_invoice",
        on_click=on_download_invoice,
        when="has_invoice",
    ),
    Button(
        Const("📥 Скачать платежку"),
        id="download_proof",
        on_click=on_download_proof,
        when="has_payment_proof",
    ),
    Button(
        Const("❌ Отменить запрос"),
        id="cancel_request",
        on_click=on_cancel_request,
        when="can_cancel",
    ),
    Button(
        Const("⬅️ Назад к списку"),
        id="back_to_list",
        on_click=on_back_to_list,
    ),
    Cancel(Const("🏠 Главное меню")),

    state=MyPaymentRequests.view_details,
    getter=get_request_details_data,
)
