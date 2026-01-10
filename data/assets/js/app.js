// Инициализация WebApp
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand(); // Раскрыть на весь экран
}

// Получаем ID пользователя из query параметров или Telegram WebApp
function getTelegramId() {
    const urlParams = new URLSearchParams(window.location.search);
    const queryId = urlParams.get('telegram_id');
    
    if (queryId) {
        return queryId;
    }
    
    // Пробуем получить из Telegram WebApp
    if (tg?.initDataUnsafe?.user?.id) {
        return String(tg.initDataUnsafe.user.id);
    }
    
    // Заглушка для тестов
    return "411840215";
}

const telegramId = getTelegramId();

// URL API (определяем автоматически)
function getApiBaseUrl() {
    // Если мы на том же домене, используем относительный путь
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://127.0.0.1:8000';
    }
    // Иначе используем относительный путь (для продакшена)
    return '';
}

const API_BASE_URL = getApiBaseUrl();
const API_URL = `${API_BASE_URL}/api/v1/course/timeline`; 

async function loadTimeline() {
    try {
        const response = await fetch(`${API_URL}?telegram_id=${telegramId}`);
        const data = await response.json();

        if (data.status === "success") {
            const progress = calculateProgress(data.timeline);
            renderHeader(data.user_name, progress);
            renderTimeline(data.timeline);
        } else {
            showError(data.message || "Ошибка загрузки курса");
        }
    } catch (error) {
        console.error("Ошибка загрузки:", error);
        showError("Ошибка загрузки курса. Попробуйте обновить страницу.");
    }
}

function calculateProgress(timeline) {
    if (!timeline || timeline.length === 0) {
        return 0;
    }
    
    const completed = timeline.filter(lesson => lesson.status === 'completed').length;
    return Math.round((completed / timeline.length) * 100);
}

function showError(message) {
    const container = document.getElementById('timeline-container');
    if (container) {
        container.innerHTML = `<p style="color: var(--color-accent); padding: 20px;">${message}</p>`;
    }
}

function renderHeader(name, progress) {
    const container = document.getElementById('header-container');
    container.innerHTML = `
        <div class="user-header__academy">
            <img src="assets/img/artchaos-icon.png" alt="ArtChaos" class="user-header__logo">
            <span>ОНЛАЙН КУРС ДЛЯ НАЧИНАЮЩИХ</span>
        </div>
        <div class="user-header__greeting">Добро пожаловать</div>
        <div class="user-header__name">${name || "Ученик"}</div>
        <div class="progress-bar">
            <div class="progress-bar__fill" style="width: ${progress}%"></div>
        </div>
    `;
}

function renderTimeline(lessons) {
    const container = document.getElementById('timeline-container');
    let html = '';

    lessons.forEach(lesson => {
        // Если это начало нового блока, добавляем заголовок
        if (lesson.is_new_block) {
            html += `<div class="block-title">Блок ${lesson.block_id || ""}</div>`;
        }

        // Определяем класс модификатора для BEM
        let modifier = '';
        let statusText = 'Доступ закрыт';
        let href = '#';
        let iconHtml = '';

        if (lesson.status === 'active') {
            modifier = 'timeline__item--active';
            statusText = 'Начать урок';
            // Ссылка на шаблон урока с параметрами
            href = `lesson_template.html?slug=${encodeURIComponent(lesson.slug)}&telegram_id=${encodeURIComponent(telegramId)}`;
        } else if (lesson.status === 'completed') {
            modifier = 'timeline__item--completed';
            statusText = 'Пройдено';
            href = `lesson_template.html?slug=${encodeURIComponent(lesson.slug)}&telegram_id=${encodeURIComponent(telegramId)}`;
            iconHtml = '<img src="assets/img/check_icon.svg" alt="Пройдено" class="lesson-card__icon">';
        } else {
            modifier = 'timeline__item--locked';
            iconHtml = '<img src="assets/img/lock_icon.svg" alt="Заблокировано" class="lesson-card__icon">';
        }

        html += `
            <div class="timeline__item ${modifier}">
                <div class="timeline__dot"></div>
                <a href="${href}" class="lesson-card">
                    <div class="lesson-card__title">${lesson.title}</div>
                    <div class="lesson-card__status">
                        ${iconHtml}
                        <span>${statusText}</span>
                    </div>
                </a>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Запуск
loadTimeline();