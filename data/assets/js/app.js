// Инициализация WebApp
const tg = window.Telegram.WebApp;
tg.expand(); // Раскрыть на весь экран

// Получаем ID пользователя
// В реальном тесте на ПК может быть пусто, поэтому ставим заглушку для тестов
const telegramId = tg.initDataUnsafe?.user?.id || "123456789"; 

// URL твоего API (если локально - http://127.0.0.1:8000)
// Когда зальешь на Amvera, поменяй на /api/v1/course/timeline
const API_URL = "http://127.0.0.1:8000/api/v1/course/timeline"; 

async function loadTimeline() {
    try {
        const response = await fetch(`${API_URL}?telegram_id=${telegramId}`);
        const data = await response.json();

        if (data.status === "success") {
            renderHeader(data.user_name);
            renderTimeline(data.timeline);
        }
    } catch (error) {
        console.error("Ошибка загрузки:", error);
        document.body.innerHTML = "<p>Ошибка загрузки курса. Попробуйте обновить.</p>";
    }
}

function renderHeader(name) {
    const container = document.getElementById('header-container');
    container.innerHTML = `
        <div class="user-header__greeting">Добро пожаловать</div>
        <div class="user-header__name">${name || "Ученик"}</div>
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

        if (lesson.status === 'active') {
            modifier = 'timeline__item--active';
            statusText = 'Начать урок';
            // Ссылка на HTML файл урока. 
            // Важно: путь относительный от index.html
            href = `${lesson.slug}.html`; 
        } else if (lesson.status === 'completed') {
            modifier = 'timeline__item--completed';
            statusText = 'Пройдено';
            href = `${lesson.slug}.html`; // Можно разрешить пересматривать
        } else {
            modifier = 'timeline__item--locked';
        }

        html += `
            <div class="timeline__item ${modifier}">
                <div class="timeline__dot"></div>
                <a href="${href}" class="lesson-card">
                    <div class="lesson-card__title">${lesson.title}</div>
                    <div class="lesson-card__status">${statusText}</div>
                </a>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Запуск
loadTimeline();