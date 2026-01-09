/**
 * Dashboard JavaScript - Основные функции для работы с dashboard
 */

// ==================== МОДАЛЬНЫЕ ОКНА ====================

/**
 * Открывает модальное окно аналитики
 */
function openAnalyticsModal() {
    const modal = document.getElementById('analytics-modal');
    if (modal) {
        modal.showModal();
    }
}

/**
 * Открывает модальное окно создания запроса на оплату
 */
function openCreateModal() {
    const modal = document.getElementById('create-payment-modal');
    if (modal) {
        modal.showModal();

        // Инициализируем Flatpickr для дат в модальном окне
        const createdDateInput = document.getElementById('modal-created-date');
        const paidDateInput = document.getElementById('modal-paid-date');
        const scheduledDateInput = document.getElementById('modal-scheduled-date');

        if (createdDateInput && !createdDateInput._flatpickr) {
            flatpickr(createdDateInput, {
                locale: 'ru',
                dateFormat: 'Y-m-d',
                allowInput: true,
                clickOpens: true,
                theme: 'light'
            });
        }

        if (paidDateInput && !paidDateInput._flatpickr) {
            flatpickr(paidDateInput, {
                locale: 'ru',
                dateFormat: 'Y-m-d',
                allowInput: true,
                clickOpens: true,
                theme: 'light'
            });
        }

        if (scheduledDateInput && !scheduledDateInput._flatpickr) {
            flatpickr(scheduledDateInput, {
                locale: 'ru',
                dateFormat: 'Y-m-d',
                allowInput: true,
                clickOpens: true,
                theme: 'light'
            });
        }
    }
}

// ==================== РАБОТА СО СТАТУСАМИ ====================

/**
 * Переключение видимости полей дат в зависимости от статуса
 */
function handleStatusChange(status) {
    const paidDateContainer = document.getElementById('modal-paid-date-container');
    const scheduledDateContainer = document.getElementById('modal-scheduled-date-container');

    if (paidDateContainer && scheduledDateContainer) {
        if (status === 'paid') {
            paidDateContainer.classList.remove('hidden');
            scheduledDateContainer.classList.add('hidden');
        } else if (status === 'scheduled') {
            paidDateContainer.classList.add('hidden');
            scheduledDateContainer.classList.remove('hidden');
        } else {
            paidDateContainer.classList.add('hidden');
            scheduledDateContainer.classList.add('hidden');
        }
    }
}

/**
 * Обновление счетчика выбранных статусов
 */
function updateStatusCount() {
    const checkboxes = document.querySelectorAll('input[name="status"]:checked');
    const count = checkboxes.length;
    const summaryText = document.getElementById('status-summary-text');

    if (summaryText) {
        if (count > 0) {
            summaryText.textContent = count + ' Selected';
        } else {
            summaryText.textContent = 'Статусы';
        }
    }
}

// ==================== ЗАГРУЗКА ФАЙЛОВ ====================

/**
 * Загрузка файла на сервер
 */
async function uploadFile(file, statusElementId, fileIdInputId, inputElement, autoSetStatus = null) {
    const statusElement = document.getElementById(statusElementId);
    const fileIdInput = document.getElementById(fileIdInputId);

    if (!file || !statusElement || !fileIdInput) {
        console.error('uploadFile: missing required elements', {
            file: !!file,
            statusElement: !!statusElement,
            fileIdInput: !!fileIdInput
        });
        return;
    }

    try {
        statusElement.textContent = 'Загрузка...';
        statusElement.className = 'text-sm text-blue-500';

        const formData = new FormData();
        formData.append('file', file);

        console.log('Uploading file:', file.name, 'size:', file.size);

        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        console.log('Upload response status:', response.status);

        if (!response.ok) {
            throw new Error('HTTP ' + response.status + ': ' + response.statusText);
        }

        const result = await response.json();
        console.log('Upload result:', result);

        if (result.success) {
            fileIdInput.value = result.file_id;
            statusElement.textContent = '✓ ' + result.filename;
            statusElement.className = 'text-sm text-green-600';

            // Автоматически устанавливаем статус если указан
            if (autoSetStatus) {
                const statusSelect = document.getElementById('modal-status');
                if (statusSelect) {
                    statusSelect.value = autoSetStatus;
                    // Блокируем изменение статуса после загрузки платёжки
                    statusSelect.disabled = true;
                    // Создаём скрытое поле для отправки статуса (disabled не отправляется)
                    let hiddenStatus = document.getElementById('modal-status-hidden');
                    if (!hiddenStatus) {
                        hiddenStatus = document.createElement('input');
                        hiddenStatus.type = 'hidden';
                        hiddenStatus.id = 'modal-status-hidden';
                        hiddenStatus.name = 'status';
                        statusSelect.parentNode.appendChild(hiddenStatus);
                    }
                    hiddenStatus.value = autoSetStatus;
                    // Вызываем handleStatusChange для обновления полей дат
                    handleStatusChange(autoSetStatus);
                }
            }
        } else {
            statusElement.textContent = '✗ Ошибка: ' + (result.error || 'Неизвестная ошибка');
            statusElement.className = 'text-sm text-red-600';
            console.error('Upload failed:', result.error);
        }
    } catch (error) {
        statusElement.textContent = '✗ Ошибка загрузки';
        statusElement.className = 'text-sm text-red-600';
        console.error('Error uploading file:', error);
    } finally {
        // Очищаем input после загрузки для возможности повторной загрузки
        if (inputElement) {
            inputElement.value = '';
        }
    }
}

// ==================== ЭКСПОРТ ====================

/**
 * Экспорт в Excel с текущими фильтрами
 */
function exportToExcel() {
    // Собираем текущие параметры фильтрации
    const params = new URLSearchParams();

    // Поиск
    const searchInput = document.getElementById('search-input');
    if (searchInput && searchInput.value) {
        params.append('search', searchInput.value);
    }

    // Статусы (чекбоксы)
    const statusCheckboxes = document.querySelectorAll('input[name="status"]:checked');
    statusCheckboxes.forEach(cb => {
        params.append('status', cb.value);
    });

    // Даты
    const dateFrom = document.getElementById('date-from');
    if (dateFrom && dateFrom.value) {
        params.append('date_from', dateFrom.value);
    }

    const dateTo = document.getElementById('date-to');
    if (dateTo && dateTo.value) {
        params.append('date_to', dateTo.value);
    }

    const dateType = document.getElementById('date-type-input');
    if (dateType && dateType.value) {
        params.append('date_type', dateType.value);
    }

    // Суммы
    const amountMin = document.getElementById('amount-min');
    if (amountMin && amountMin.value) {
        params.append('amount_min', amountMin.value);
    }

    const amountMax = document.getElementById('amount-max');
    if (amountMax && amountMax.value) {
        params.append('amount_max', amountMax.value);
    }

    // Создатель (radio)
    const creatorRadio = document.querySelector('input[name="creator_id"]:checked');
    if (creatorRadio && creatorRadio.value) {
        params.append('creator_id', creatorRadio.value);
    }

    // Формируем URL и открываем для скачивания
    const exportUrl = '/export/excel?' + params.toString();
    window.location.href = exportUrl;
}

// ==================== ФИЛЬТРЫ И ДАТА ====================

/**
 * Переключение типа даты
 */
function switchDateType(type) {
    // Обновляем скрытое поле
    const dateTypeInput = document.getElementById('date-type-input');
    if (dateTypeInput) {
        dateTypeInput.value = type;
    }

    // Переключаем активные классы табов
    const allTabs = document.querySelectorAll('.date-type-tab');
    allTabs.forEach(tab => {
        if (tab.getAttribute('data-date-type') === type) {
            tab.classList.remove('btn-ghost');
            tab.classList.add('btn-primary');
        } else {
            tab.classList.remove('btn-primary');
            tab.classList.add('btn-ghost');
        }
    });
}

/**
 * Переключение стрелки для dropdown создателей
 */
function toggleCreatorArrow() {
    const dropdown = document.getElementById('creator-dropdown');
    const arrow = document.getElementById('creator-arrow');

    if (arrow) {
        setTimeout(() => {
            if (dropdown.hasAttribute('open')) {
                arrow.textContent = '▲';
                arrow.classList.add('text-primary');
            } else {
                arrow.textContent = '▼';
                arrow.classList.remove('text-primary');
            }
        }, 10);
    }
}

/**
 * Обновление текста создателя
 */
function updateCreatorText(radio) {
    const summaryText = document.getElementById('creator-summary-text');

    if (summaryText) {
        if (radio.value === '') {
            summaryText.textContent = '👤 Все создатели';
        } else {
            const label = radio.closest('label');
            const nameSpan = label ? label.querySelector('span') : null;
            const displayName = nameSpan ? nameSpan.textContent.trim() : 'Создатель';
            summaryText.textContent = '👤 ' + displayName;
        }
    }
}

/**
 * Обработчик для dropdown статусов (переключение стрелки)
 */
function toggleStatusArrow(event) {
    const arrow = document.getElementById('status-arrow');
    const details = event.target;

    if (arrow) {
        setTimeout(() => {
            if (details.hasAttribute('open')) {
                arrow.textContent = '▲';
                arrow.classList.add('text-primary');
            } else {
                arrow.textContent = '▼';
                arrow.classList.remove('text-primary');
            }
        }, 10);
    }
}

// ==================== ТАБЛИЦА И ПАГИНАЦИЯ ====================

/**
 * Обновление таблицы через AJAX
 */
async function updateTable(url) {
    const tableContainer = document.getElementById('table-container');
    if (!tableContainer) return;

    try {
        // Показываем индикатор загрузки
        tableContainer.style.opacity = '0.5';

        const response = await fetch(url);
        const html = await response.text();

        // Создаем временный контейнер для парсинга HTML
        const temp = document.createElement('div');
        temp.innerHTML = html;

        // Находим новый контейнер таблицы
        const newTableContainer = temp.querySelector('#table-container');
        if (newTableContainer) {
            tableContainer.innerHTML = newTableContainer.innerHTML;
        }

        // Обновляем скрытое поле per_page из URL ПОСЛЕ замены HTML
        const urlParams = new URLSearchParams(url.split('?')[1]);
        const perPageInput = document.getElementById('per-page-input');

        // per_page_selector теперь новый элемент после замены innerHTML
        const perPageSelector = document.getElementById('per-page-selector');

        if (perPageInput && urlParams.has('per_page')) {
            perPageInput.value = urlParams.get('per_page');
        }

        // Устанавливаем значение для нового selector
        if (perPageSelector) {
            const perPageValue = urlParams.get('per_page') || '20';
            perPageSelector.value = perPageValue;
            console.log('Updated per_page selector to:', perPageValue);
        }

        // Убираем индикатор загрузки
        tableContainer.style.opacity = '1';

        // Обновляем URL без перезагрузки
        window.history.pushState({}, '', url);
    } catch (error) {
        console.error('Ошибка при обновлении таблицы:', error);
        tableContainer.style.opacity = '1';
    }
}

/**
 * Обработчик submit формы фильтров
 */
function handleFilterSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const params = new URLSearchParams();

    // Добавляем только заполненные параметры
    for (const [key, value] of formData.entries()) {
        if (value && value.trim() !== '') {
            params.append(key, value);
        }
    }

    // Убедимся что per_page всегда передается
    if (!params.has('per_page')) {
        const perPageInput = document.getElementById('per-page-input');
        if (perPageInput && perPageInput.value) {
            params.set('per_page', perPageInput.value);
        } else {
            params.set('per_page', '20'); // Дефолтное значение
        }
    }

    // Сбрасываем на первую страницу при новом поиске
    params.set('page', '1');

    const url = '/dashboard?' + params.toString();
    updateTable(url);
}

/**
 * Обработчик кнопки сброса фильтров
 */
function handleResetFilters(event) {
    event.preventDefault();
    const perPage = document.getElementById('per-page-input').value;
    const url = '/dashboard?per_page=' + perPage;
    updateTable(url);

    // Очищаем форму
    const form = document.getElementById('filters-form');
    if (form) {
        form.reset();
        // Снимаем все чекбоксы статусов
        form.querySelectorAll('input[name="status"]').forEach(cb => cb.checked = false);
        updateStatusCount();
    }
}

/**
 * Обработчик кликов по пагинации
 */
function handlePaginationClick(event) {
    event.preventDefault();
    const link = event.target.closest('.pagination-link');
    if (!link || link.classList.contains('btn-disabled')) return;

    const page = link.getAttribute('data-page');
    if (!page) return;

    // Получаем текущие параметры формы
    const form = document.getElementById('filters-form');
    const formData = new FormData(form);
    const params = new URLSearchParams();

    // Добавляем только заполненные параметры
    for (const [key, value] of formData.entries()) {
        if (value && value.trim() !== '') {
            params.append(key, value);
        }
    }

    // Устанавливаем новую страницу
    params.set('page', page);

    const url = '/dashboard?' + params.toString();
    updateTable(url);
}

/**
 * Обработчик изменения количества записей на странице
 */
function handlePerPageChange(perPage) {
    // Обновляем скрытое поле в форме
    const perPageInput = document.getElementById('per-page-input');
    if (perPageInput) {
        perPageInput.value = perPage;
    }

    // Получаем текущие параметры формы
    const form = document.getElementById('filters-form');
    const formData = new FormData(form);
    const params = new URLSearchParams();

    // Добавляем только заполненные параметры
    for (const [key, value] of formData.entries()) {
        if (value && value.trim() !== '' && key !== 'per_page') {
            params.append(key, value);
        }
    }

    // Устанавливаем новое значение per_page и сбрасываем на первую страницу
    params.set('per_page', perPage);
    params.set('page', '1');

    console.log('handlePerPageChange - URL:', '/dashboard?' + params.toString());

    const url = '/dashboard?' + params.toString();
    updateTable(url);
}

/**
 * Автоматическое применение фильтров
 */
function autoApplyFilters() {
    const form = document.getElementById('filters-form');
    if (form) {
        const formData = new FormData(form);
        const params = new URLSearchParams();

        // Добавляем только заполненные параметры
        for (const [key, value] of formData.entries()) {
            if (value && value.trim() !== '') {
                params.append(key, value);
            }
        }

        // Убедимся что per_page всегда передается
        if (!params.has('per_page')) {
            const perPageInput = document.getElementById('per-page-input');
            if (perPageInput && perPageInput.value) {
                params.set('per_page', perPageInput.value);
            } else {
                params.set('per_page', '20');
            }
        }

        // Сбрасываем на первую страницу при изменении фильтров
        params.set('page', '1');

        const url = '/dashboard?' + params.toString();
        updateTable(url);
    }
}

// ==================== DEBOUNCE ====================

let searchTimeout;

/**
 * Debounce функция для поиска
 */
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(function() {
        autoApplyFilters();
    }, 500); // 500ms задержка
}

// ==================== ИНИЦИАЛИЗАЦИЯ ====================

document.addEventListener('DOMContentLoaded', function() {
    // Конфигурация для русской локализации и кастомного стиля
    const config = {
        locale: 'ru',
        dateFormat: 'Y-m-d',
        allowInput: true,
        clickOpens: true,
        theme: 'light',
        onChange: function() {
            autoApplyFilters(); // Автообновление при изменении даты
        }
    };

    // Инициализация календарей
    const dateFromInput = document.getElementById('date_from_picker');
    const dateToInput = document.getElementById('date_to_picker');

    if (dateFromInput) {
        flatpickr(dateFromInput, config);
    }

    if (dateToInput) {
        flatpickr(dateToInput, config);
    }

    // Добавляем обработчик клика для dropdown статусов
    const statusDropdown = document.getElementById('status-dropdown');
    if (statusDropdown) {
        statusDropdown.addEventListener('toggle', toggleStatusArrow);
    }

    // Добавляем обработчик формы фильтров
    const filtersForm = document.getElementById('filters-form');
    if (filtersForm) {
        filtersForm.addEventListener('submit', handleFilterSubmit);

        // Автообновление при изменении чекбоксов статусов
        filtersForm.querySelectorAll('input[name="status"]').forEach(function(checkbox) {
            checkbox.addEventListener('change', autoApplyFilters);
        });

        // Автообновление при изменении радиокнопок создателя
        filtersForm.querySelectorAll('input[name="creator_id"]').forEach(function(radio) {
            radio.addEventListener('change', autoApplyFilters);
        });

        // Автообновление при изменении полей сумм (с небольшой задержкой)
        const amountMinInput = filtersForm.querySelector('input[name="amount_min"]');
        const amountMaxInput = filtersForm.querySelector('input[name="amount_max"]');
        if (amountMinInput) {
            amountMinInput.addEventListener('input', debounceSearch);
        }
        if (amountMaxInput) {
            amountMaxInput.addEventListener('input', debounceSearch);
        }

        // Автообновление при вводе в поиск (с задержкой)
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', debounceSearch);
        }
    }

    // Добавляем обработчик кнопки сброса
    const resetBtn = document.getElementById('reset-filters-btn');
    if (resetBtn) {
        resetBtn.addEventListener('click', handleResetFilters);
    }

    // Используем event delegation для пагинации (так как она обновляется динамически)
    document.addEventListener('click', function(event) {
        if (event.target.closest('.pagination-link')) {
            handlePaginationClick(event);
        }
    });

    // Закрытие dropdown при клике вне его области
    document.addEventListener('click', function(event) {
        // Проверяем все открытые details элементы
        const openDetails = document.querySelectorAll('details[open]');

        openDetails.forEach(function(details) {
            // Проверяем, был ли клик вне этого dropdown
            if (!details.contains(event.target)) {
                details.removeAttribute('open');

                // Обновляем стрелки при закрытии
                if (details.id === 'status-dropdown') {
                    const arrow = document.getElementById('status-arrow');
                    if (arrow) {
                        arrow.textContent = '▼';
                        arrow.classList.remove('text-primary');
                    }
                } else if (details.id === 'creator-dropdown') {
                    const arrow = document.getElementById('creator-arrow');
                    if (arrow) {
                        arrow.textContent = '▼';
                        arrow.classList.remove('text-primary');
                    }
                }
            }
        });
    });

    // Обработка отправки формы создания платежа
    const createForm = document.getElementById('create-payment-form');
    if (createForm) {
        createForm.addEventListener('submit', async function(event) {
            event.preventDefault();

            const formData = new FormData(createForm);
            const submitBtn = createForm.querySelector('button[type="submit"]');

            // Дизейблим кнопку
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Создание...';
            }

            try {
                const response = await fetch('/payment/create', {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    // Закрываем модальное окно
                    const modal = document.getElementById('create-payment-modal');
                    if (modal) {
                        modal.close();
                    }

                    // Очищаем форму
                    createForm.reset();

                    // Сбрасываем скрытые поля file_id
                    const invoiceFileId = document.getElementById('modal-invoice-file-id');
                    if (invoiceFileId) invoiceFileId.value = '';
                    const paymentFileId = document.getElementById('modal-payment-file-id');
                    if (paymentFileId) paymentFileId.value = '';

                    // Сбрасываем статусы загрузки файлов
                    const invoiceStatus = document.getElementById('modal-invoice-status');
                    if (invoiceStatus) {
                        invoiceStatus.textContent = '';
                        invoiceStatus.className = 'text-sm';
                    }
                    const paymentStatus = document.getElementById('modal-payment-status');
                    if (paymentStatus) {
                        paymentStatus.textContent = '';
                        paymentStatus.className = 'text-sm';
                    }

                    // Разблокируем селектор статуса и удаляем скрытое поле
                    const statusSelect = document.getElementById('modal-status');
                    if (statusSelect) {
                        statusSelect.disabled = false;
                        statusSelect.value = 'pending';
                    }
                    const hiddenStatus = document.getElementById('modal-status-hidden');
                    if (hiddenStatus) hiddenStatus.remove();

                    // Сбрасываем поля дат
                    handleStatusChange('pending');

                    // Обновляем таблицу
                    const currentParams = new URLSearchParams(window.location.search);
                    const url = '/dashboard?' + currentParams.toString();
                    await updateTable(url);
                } else {
                    alert('Ошибка при создании запроса');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                alert('Ошибка при создании запроса');
            } finally {
                // Возвращаем кнопку в исходное состояние
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Создать';
                }
            }
        });
    }

    // Обработчики загрузки файлов
    const invoiceFileInput = document.getElementById('modal-invoice-file');
    if (invoiceFileInput) {
        invoiceFileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                uploadFile(file, 'modal-invoice-status', 'modal-invoice-file-id', invoiceFileInput);
            }
        });
    }

    const paymentFileInput = document.getElementById('modal-payment-file');
    if (paymentFileInput) {
        paymentFileInput.addEventListener('change', function(event) {
            const file = event.target.files[0];
            if (file) {
                // При загрузке платёжки автоматически ставим статус "Оплачен"
                uploadFile(file, 'modal-payment-status', 'modal-payment-file-id', paymentFileInput, 'paid');
            }
        });
    }
});
