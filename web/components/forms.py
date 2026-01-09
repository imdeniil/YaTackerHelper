"""Form компоненты"""

from datetime import datetime
from fasthtml.common import *
from bot.database.models import User, UserRole


def create_payment_form() -> Form:
    """Форма создания запроса на оплату (старая версия)"""
    return Form(
        # Название
        Div(
            Label("Название для плательщика", cls="label"),
            Input(
                type="text",
                name="title",
                placeholder="Например: Оплата за услуги",
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control"
        ),

        # Сумма
        Div(
            Label("Сумма (₽)", cls="label"),
            Input(
                type="text",
                name="amount",
                placeholder="50000",
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control"
        ),

        # Комментарий
        Div(
            Label("Комментарий", cls="label"),
            Textarea(
                name="comment",
                placeholder="Дополнительная информация о платеже...",
                required=True,
                rows=3,
                cls="textarea textarea-bordered w-full"
            ),
            cls="form-control"
        ),

        # Кнопка отправки
        Button(
            "Создать запрос",
            type="submit",
            cls="btn btn-primary w-full mt-4"
        ),

        method="POST",
        action="/payment/create"
    )


def create_payment_modal(user_role: str = "worker") -> Div:
    """Модальное окно для создания запроса на оплату с разными полями по ролям

    Args:
        user_role: Роль пользователя (worker, manager, owner)
    """
    today = datetime.now().strftime("%Y-%m-%d")

    # Определяем доступные поля для роли
    is_manager_or_owner = user_role.lower() in ["manager", "owner"]

    return Div(
        # Модальное окно
        Dialog(
            Div(
                # Заголовок
                Div(
                    H3("Создать запрос на оплату", cls="font-bold text-lg"),
                    Button(
                        "✕",
                        type="button",
                        cls="btn btn-sm btn-circle btn-ghost absolute right-2 top-2",
                        onclick="document.getElementById('create-payment-modal').close()"
                    ),
                    cls="relative"
                ),

                # Форма
                Form(
                    # Название
                    Div(
                        Label("Название для плательщика", cls="label"),
                        Input(
                            type="text",
                            name="title",
                            id="modal-title",
                            placeholder="Например: Оплата за услуги",
                            required=True,
                            cls="input input-bordered input-sm w-full"
                        ),
                        cls="form-control mb-3"
                    ),

                    # Сумма
                    Div(
                        Label("Сумма (₽)", cls="label"),
                        Input(
                            type="text",
                            name="amount",
                            id="modal-amount",
                            placeholder="50000",
                            required=True,
                            cls="input input-bordered input-sm w-full"
                        ),
                        cls="form-control mb-3"
                    ),

                    # Комментарий
                    Div(
                        Label("Комментарий", cls="label"),
                        Textarea(
                            name="comment",
                            id="modal-comment",
                            placeholder="Дополнительная информация о платеже...",
                            required=True,
                            rows=4,
                            cls="textarea textarea-bordered textarea-sm w-full"
                        ),
                        cls="form-control mb-3"
                    ),

                    # Дополнительные поля для Manager/Owner
                    *(
                        [
                            # Статус
                            Div(
                                Label("Статус", cls="label"),
                                Select(
                                    Option("⏳ Ожидает", value="pending", selected=True),
                                    Option("✅ Оплачено", value="paid"),
                                    Option("📅 Запланирован", value="scheduled"),
                                    name="status",
                                    id="modal-status",
                                    cls="select select-bordered select-sm w-full",
                                    onchange="handleStatusChange(this.value)"
                                ),
                                cls="form-control mb-3"
                            ),

                            # Дата создания
                            Div(
                                Label("Дата создания", cls="label"),
                                Input(
                                    type="text",
                                    name="created_date",
                                    id="modal-created-date",
                                    value=today,
                                    placeholder="Выберите дату",
                                    cls="input input-bordered input-sm w-full",
                                    readonly=True
                                ),
                                cls="form-control mb-3"
                            ),

                            # Дата оплаты (показывается если статус = paid)
                            Div(
                                Label("Дата оплаты", cls="label"),
                                Input(
                                    type="text",
                                    name="paid_date",
                                    id="modal-paid-date",
                                    value=today,
                                    placeholder="Выберите дату",
                                    cls="input input-bordered input-sm w-full",
                                    readonly=True
                                ),
                                cls="form-control mb-3 hidden",
                                id="modal-paid-date-container"
                            ),

                            # Дата планирования (показывается если статус = scheduled)
                            Div(
                                Label("Дата планирования", cls="label"),
                                Input(
                                    type="text",
                                    name="scheduled_date",
                                    id="modal-scheduled-date",
                                    value=today,
                                    placeholder="Выберите дату",
                                    cls="input input-bordered input-sm w-full",
                                    readonly=True
                                ),
                                cls="form-control mb-3 hidden",
                                id="modal-scheduled-date-container"
                            ),
                        ] if is_manager_or_owner else []
                    ),

                    # Файл счета (для всех ролей)
                    Div(
                        Label("Счет (необязательно)", cls="label"),
                        Input(
                            type="file",
                            id="modal-invoice-file",
                            accept=".pdf,.jpg,.jpeg,.png",
                            cls="file-input file-input-bordered file-input-sm w-full"
                        ),
                        Input(type="hidden", name="invoice_file_id", id="modal-invoice-file-id", value=""),
                        Span("", id="modal-invoice-status", cls="text-sm text-gray-500"),
                        cls="form-control mb-3"
                    ),

                    # Файл платежки (для Manager/Owner)
                    *(
                        [
                            Div(
                                Label("Платежка (необязательно)", cls="label"),
                                Input(
                                    type="file",
                                    id="modal-payment-file",
                                    accept=".pdf,.jpg,.jpeg,.png",
                                    cls="file-input file-input-bordered file-input-sm w-full"
                                ),
                                Input(type="hidden", name="payment_file_id", id="modal-payment-file-id", value=""),
                                Span("", id="modal-payment-status", cls="text-sm text-gray-500"),
                                cls="form-control mb-3"
                            ),
                        ] if is_manager_or_owner else []
                    ),

                    # Кнопки действий
                    Div(
                        Button(
                            "Отмена",
                            type="button",
                            cls="btn btn-ghost btn-sm",
                            onclick="document.getElementById('create-payment-modal').close()"
                        ),
                        Button(
                            "Создать",
                            type="submit",
                            cls="btn btn-primary btn-sm"
                        ),
                        cls="flex justify-end gap-2"
                    ),

                    method="POST",
                    action="/payment/create",
                    id="create-payment-form"
                ),

                cls="modal-box"
            ),
            # Backdrop для закрытия при клике вне модального окна
            Form(
                Button(type="submit", cls="cursor-default"),
                method="dialog",
                cls="modal-backdrop"
            ),
            id="create-payment-modal",
            cls="modal"
        ),
        id="create-modal-container"
    )


def schedule_payment_form(request_id: int) -> Form:
    """Форма планирования оплаты"""
    return Form(
        # Выбор "Сегодня" или "На дату"
        Div(
            Label("Когда оплатить?", cls="label"),
            Div(
                Label(
                    Input(type_="radio", name="schedule_type", value="today", cls="radio", checked=True),
                    Span("Сегодня", cls="ml-2"),
                    cls="label cursor-pointer justify-start gap-2"
                ),
                Label(
                    Input(type_="radio", name="schedule_type", value="date", cls="radio"),
                    Span("На определенную дату", cls="ml-2"),
                    cls="label cursor-pointer justify-start gap-2"
                ),
                cls="space-y-2"
            ),
            cls="form-control mb-4"
        ),

        # Поле даты (скрывается/показывается в зависимости от выбора)
        Div(
            Label("Дата оплаты", cls="label"),
            Input(
                type_="date",
                name="scheduled_date",
                cls="input input-bordered w-full",
                id="scheduled_date_input"
            ),
            cls="form-control",
            id="date_field",
            style="display: none;"
        ),

        # Кнопка отправки
        Button(
            "Запланировать",
            type_="submit",
            cls="btn btn-primary w-full mt-4"
        ),

        # JavaScript для показа/скрытия поля даты
        Script("""
            document.querySelectorAll('input[name="schedule_type"]').forEach(radio => {
                radio.addEventListener('change', function() {
                    const dateField = document.getElementById('date_field');
                    const dateInput = document.getElementById('scheduled_date_input');
                    if (this.value === 'date') {
                        dateField.style.display = 'block';
                        dateInput.required = true;
                    } else {
                        dateField.style.display = 'none';
                        dateInput.required = false;
                    }
                });
            });
        """),

        method="POST",
        action=f"/payment/{request_id}/schedule"
    )


def mark_as_paid_form(request_id: int) -> Form:
    """Форма отметки как оплаченного (упрощенная версия без загрузки файла)"""
    return Form(
        Div(
            P("После отметки как оплаченный, запрос будет закрыт.", cls="text-sm opacity-70 mb-4"),
            P("Загрузка платежного документа будет доступна через Telegram бот.", cls="text-sm opacity-70 mb-4"),
            cls="mb-4"
        ),

        # Кнопка отправки
        Button(
            "Отметить как оплаченный",
            type_="submit",
            cls="btn btn-success w-full",
            onclick="return confirm('Вы уверены что хотите отметить этот запрос как оплаченный?')"
        ),

        method="POST",
        action=f"/payment/{request_id}/pay"
    )


def user_edit_form(user: User) -> Form:
    """Форма редактирования пользователя"""
    return Form(
        # ФИО
        Div(
            Label("ФИО", cls="label"),
            Input(
                type_="text",
                name="display_name",
                value=user.display_name,
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Username
        Div(
            Label("Telegram Username (без @)", cls="label"),
            Input(
                type_="text",
                name="telegram_username",
                value=user.telegram_username,
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Tracker Login
        Div(
            Label("Логин в Yandex Tracker (опционально)", cls="label"),
            Input(
                type_="text",
                name="tracker_login",
                value=user.tracker_login or "",
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Роль
        Div(
            Label("Роль", cls="label"),
            Select(
                Option("👑 Владелец", value=UserRole.OWNER.value, selected=user.role == UserRole.OWNER),
                Option("📊 Менеджер", value=UserRole.MANAGER.value, selected=user.role == UserRole.MANAGER),
                Option("👷 Сотрудник", value=UserRole.WORKER.value, selected=user.role == UserRole.WORKER),
                name="role",
                required=True,
                cls="select select-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Плательщик
        Div(
            Label(
                Input(
                    type="checkbox",
                    name="is_billing_contact",
                    value="true",
                    checked="1" if user.is_billing_contact else None,
                    cls="checkbox checkbox-primary"
                ),
                Span("Плательщик", cls="label-text ml-3"),
                cls="label cursor-pointer justify-start"
            ),
            cls="form-control mb-4"
        ),

        # Кнопки
        Div(
            Button("Сохранить", type_="submit", cls="btn btn-primary"),
            A("Отмена", href="/users", cls="btn btn-ghost"),
            cls="flex gap-2"
        ),

        method="POST",
        action=f"/users/{user.id}/edit"
    )


def user_create_form() -> Form:
    """Форма создания нового пользователя"""
    return Form(
        # ФИО
        Div(
            Label("ФИО", cls="label"),
            Input(
                type_="text",
                name="display_name",
                placeholder="Иванов Иван Иванович",
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Username
        Div(
            Label("Telegram Username (без @)", cls="label"),
            Input(
                type_="text",
                name="telegram_username",
                placeholder="username",
                required=True,
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Tracker Login
        Div(
            Label("Логин в Yandex Tracker (опционально)", cls="label"),
            Input(
                type_="text",
                name="tracker_login",
                placeholder="i.ivanov",
                cls="input input-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Роль
        Div(
            Label("Роль", cls="label"),
            Select(
                Option("👷 Сотрудник", value=UserRole.WORKER.value, selected=True),
                Option("📊 Менеджер", value=UserRole.MANAGER.value),
                Option("👑 Владелец", value=UserRole.OWNER.value),
                name="role",
                required=True,
                cls="select select-bordered w-full"
            ),
            cls="form-control mb-4"
        ),

        # Плательщик
        Div(
            Label(
                Input(
                    type="checkbox",
                    name="is_billing_contact",
                    value="true",
                    cls="checkbox checkbox-primary"
                ),
                Span("Плательщик", cls="label-text ml-3"),
                cls="label cursor-pointer justify-start"
            ),
            cls="form-control mb-4"
        ),

        # Кнопки
        Div(
            Button("Создать", type_="submit", cls="btn btn-primary"),
            A("Отмена", href="/users", cls="btn btn-ghost"),
            cls="flex gap-2"
        ),

        method="POST",
        action="/users/create"
    )
