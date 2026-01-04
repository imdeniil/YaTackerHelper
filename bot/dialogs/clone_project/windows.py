"""Window definitions для диалога клонирования проекта"""

from operator import itemgetter
from aiogram import F
from aiogram_dialog import Window
from aiogram_dialog.widgets.kbd import Button, Back, Cancel, Select, ScrollingGroup, Url
from aiogram_dialog.widgets.text import Const, Format, Progress
from aiogram_dialog.widgets.input import MessageInput

from bot.states import CloneProject
from .getters import (
    get_select_project_data,
    get_confirm_data,
    get_new_name_data,
    get_queue_data,
    get_final_confirm_data,
)
from .handlers import (
    on_project_selected,
    on_confirm_project,
    on_new_name_input,
    on_use_default_queue,
    on_enter_custom_queue,
    on_clone_queue_selected,
    on_start_clone,
    on_message_during_clone,
)


# Окно 1: Выбор проекта
select_project_window = Window(
    Const("Выберите проект для клонирования:", when="count"),
    Const("❌ Не найдено проектов со словом 'шаблон'", when=lambda data, widget, manager: not data.get("count")),
    ScrollingGroup(
        Select(
            Format("{item[0]}"),  # Отображаем название проекта
            id="project_select",
            item_id_getter=itemgetter(1),  # ID проекта берем из второго элемента кортежа
            items="projects",
            on_click=on_project_selected,
        ),
        id="projects_scroll",
        width=1,
        height=5,
        when="count",  # Показываем только если есть проекты
    ),
    Cancel(Const("❌ Отмена")),
    state=CloneProject.select_project,
    getter=get_select_project_data,
)

# Окно 2: Подтверждение проекта
confirm_project_window = Window(
    Format("📁 Проект: <b>{project_name}</b>\n"),
    Button(
        Const("✅ Продолжить"),
        id="confirm_project",
        on_click=on_confirm_project,
    ),
    Back(Const("◀️ Назад")),
    state=CloneProject.confirm_project,
    getter=get_confirm_data,
)

# Окно 3: Ввод имени нового проекта
enter_new_name_window = Window(
    Format("Клонируется проект: <b>{project_name}</b>\n"),
    Const("Введите название для нового проекта:"),
    MessageInput(on_new_name_input),
    Back(Const("◀️ Назад")),
    state=CloneProject.enter_new_name,
    getter=get_new_name_data,
)

# Окно 4: Выбор целевой очереди
enter_queue_window = Window(
    Format("Новый проект: <b>{new_name}</b>\n"),
    # Если есть дефолтная очередь и не в режиме выбора из списка
    Format(
        "Очередь из настроек: <code>{default_queue}</code>\n\n"
        "Использовать эту очередь или выбрать другую?",
        when=lambda data, widget, manager: data.get("has_default") and data.get("queue_step") == "",
    ),
    Button(
        Const("✅ Использовать"),
        id="use_default_queue",
        on_click=on_use_default_queue,
        when=lambda data, widget, manager: data.get("has_default") and data.get("queue_step") == "",
    ),
    Button(
        Const("📋 Выбрать другую"),
        id="enter_custom_queue",
        on_click=on_enter_custom_queue,
        when=lambda data, widget, manager: data.get("has_default") and data.get("queue_step") == "",
    ),
    # Выбор из списка (если нет дефолта или выбран режим выбора из списка)
    Const(
        "Выберите очередь из списка:",
        when=lambda data, widget, manager: not data.get("has_default") or data.get("queue_step") == "select_queue_list",
    ),
    ScrollingGroup(
        Select(
            Format("{item[name]} ({item[key]})"),
            id="clone_queue_select",
            item_id_getter=lambda x: x["key"],
            items="queues",
            on_click=on_clone_queue_selected,
        ),
        id="clone_queues_scroll",
        width=1,
        height=5,
        when=lambda data, widget, manager: not data.get("has_default") or data.get("queue_step") == "select_queue_list",
    ),
    Back(Const("◀️ Назад")),
    state=CloneProject.enter_queue,
    getter=get_queue_data,
)

# Окно 5: Динамическое окно (подтверждение/прогресс/результат)
confirm_clone_window = Window(
    # === СОСТОЯНИЕ 1: Подтверждение (is_cloning=False, result=None) ===
    Format("📁 Исходный проект: <b>{project_name}</b>", when=~F["is_cloning"] & ~F["result"]),
    Format("📝 Новый проект: <b>{new_name}</b>", when=~F["is_cloning"] & ~F["result"]),
    Format("📮 Очередь: <b>{queue}</b>\n", when=~F["is_cloning"] & ~F["result"]),
    Const("⚠️ Начать клонирование?", when=~F["is_cloning"] & ~F["result"]),
    Button(
        Const("🚀 Начать"),
        id="start_clone",
        on_click=on_start_clone,
        when=~F["is_cloning"] & ~F["result"]
    ),
    Back(Const("◀️ Назад"), when=~F["is_cloning"] & ~F["result"]),

    # === СОСТОЯНИЕ 2: Клонирование (is_cloning=True) ===
    Format("\n{phase}\n", when=F["is_cloning"]),
    Progress("progress", 10, when=F["is_cloning"]),

    # === СОСТОЯНИЕ 3: Результат (is_cloning=False, result есть) ===
    # Успех
    Format("📁 Проект: <b>{new_project_name}</b>", when=~F["is_cloning"] & F["result"]),
    Format("📋 Создано задач: <b>{created_count}</b>\n", when=~F["is_cloning"] & F["result"]),
    Url(
        Const("🔗 Открыть проект"),
        Format("{project_url}"),
        when=~F["is_cloning"] & F["result"]
    ),
    Cancel(Const("🏠 Главное меню"), when=~F["is_cloning"] & F["result"]),

    # Ошибка
    Const("❌ <b>Ошибка клонирования</b>\n", when=~F["is_cloning"] & ~F["result"] & F["error"]),
    Format("⚠️ {error}\n", when=~F["is_cloning"] & ~F["result"] & F["error"]),
    Const("💡 Проверьте права доступа и повторите попытку.", when=~F["is_cloning"] & ~F["result"] & F["error"]),
    Cancel(Const("🏠 Главное меню"), when=~F["is_cloning"] & ~F["result"] & F["error"]),

    # Предотвращаем сброс во время выполнения
    MessageInput(on_message_during_clone),

    state=CloneProject.confirm_clone,
    getter=get_final_confirm_data,
)
