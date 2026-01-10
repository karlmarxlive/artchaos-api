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

// Глобальные переменные для хранения данных
let allLessons = [];
let blocksData = {};
let currentBlockId = null;

async function loadTimeline() {
    try {
        const response = await fetch(`${API_URL}?telegram_id=${telegramId}`);
        const data = await response.json();

        if (data.status === "success") {
            allLessons = data.timeline;
            blocksData = groupLessonsByBlock(allLessons);
            
            renderHeader(data.user_name);
            renderBlockMenu(blocksData);
            
            // По умолчанию показываем первый блок
            const blockIds = Object.keys(blocksData);
            if (blockIds.length > 0) {
                currentBlockId = blockIds[0];
                renderTimeline(blocksData[currentBlockId]);
            }
        } else {
            showError(data.message || "Ошибка загрузки курса");
        }
    } catch (error) {
        console.error("Ошибка загрузки:", error);
        showError("Ошибка загрузки курса. Попробуйте обновить страницу.");
    }
}

// Группировка уроков по блокам
function groupLessonsByBlock(lessons) {
    const groups = {};
    
    lessons.forEach(lesson => {
        const blockId = lesson.block_id || 'unknown';
        if (!groups[blockId]) {
            groups[blockId] = [];
        }
        groups[blockId].push(lesson);
    });
    
    return groups;
}

function showError(message) {
    const container = document.getElementById('timeline-container');
    if (container) {
        container.innerHTML = `<p style="color: var(--color-accent); padding: 20px;">${message}</p>`;
    }
}

function renderHeader(name) {
    const container = document.getElementById('header-container');
    container.innerHTML = `
        <div class="user-header__academy">
            <img src="assets/img/artchaos-icon.png" alt="ArtChaos" class="user-header__logo">
            <span>ОНЛАЙН КУРС ДЛЯ НАЧИНАЮЩИХ</span>
        </div>
        <div class="user-header__greeting">Добро пожаловать,</div>
        <div class="user-header__name">${name || "Ученик"}</div>
    `;
}

// Рендер меню блоков (pills)
function renderBlockMenu(blocksData) {
    const blockIds = Object.keys(blocksData);
    if (blockIds.length <= 1) {
        // Если только один блок, меню не показываем
        return;
    }
    
    const menuContainer = document.createElement('div');
    menuContainer.className = 'block-menu';
    menuContainer.id = 'block-menu';
    
    blockIds.forEach((blockId, index) => {
        const button = document.createElement('button');
        button.className = 'block-menu__item';
        button.textContent = `Блок ${blockId}`;
        button.dataset.blockId = blockId;
        
        // Первый блок активен по умолчанию
        if (index === 0) {
            button.classList.add('block-menu__item--active');
        }
        
        button.addEventListener('click', () => switchBlock(blockId));
        menuContainer.appendChild(button);
    });
    
    // Вставляем меню перед таймлайном
    const timelineContainer = document.getElementById('timeline-container');
    timelineContainer.parentNode.insertBefore(menuContainer, timelineContainer);
}

// Переключение между блоками с анимацией
function switchBlock(newBlockId) {
    if (newBlockId === currentBlockId) return;
    
    const container = document.getElementById('timeline-container');
    const items = container.querySelectorAll('.timeline__item');
    
    // Обновляем активную кнопку в меню
    document.querySelectorAll('.block-menu__item').forEach(btn => {
        btn.classList.remove('block-menu__item--active');
        if (btn.dataset.blockId === newBlockId) {
            btn.classList.add('block-menu__item--active');
        }
    });
    
    // Fade-out текущих элементов
    items.forEach(item => {
        item.classList.add('timeline__item--fade-out');
    });
    
    // После анимации меняем контент
    setTimeout(() => {
        currentBlockId = newBlockId;
        renderTimeline(blocksData[newBlockId]);
        
        // Fade-in новых элементов
        const newItems = container.querySelectorAll('.timeline__item');
        newItems.forEach((item, index) => {
            item.classList.add('timeline__item--fade-out');
            // Небольшая задержка для каждого элемента
            setTimeout(() => {
                item.classList.remove('timeline__item--fade-out');
                item.classList.add('timeline__item--fade-in');
            }, index * 50);
        });
    }, 300);
}

function renderTimeline(lessons) {
    const container = document.getElementById('timeline-container');
    let html = '';
    
    // Считаем пройденные уроки для линии прогресса
    let completedCount = 0;
    let totalCount = lessons.length;
    
    lessons.forEach((lesson, index) => {
        if (lesson.status === 'completed') {
            completedCount++;
        }
        
        // Определяем класс модификатора для BEM
        let modifier = '';
        let statusText = 'Доступ закрыт';
        let href = '#';
        let iconHtml = '';

        if (lesson.status === 'active') {
            modifier = 'timeline__item--active';
            statusText = 'Начать урок';
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
            <div class="timeline__item ${modifier}" data-index="${index}">
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
    
    // Добавляем линию прогресса
    updateProgressLine(completedCount, totalCount);
}

// Обновление вертикальных линий (пунктирной и прогресса)
function updateProgressLine(completedCount, totalCount) {
    const container = document.getElementById('timeline-container');
    const items = container.querySelectorAll('.timeline__item');
    
    // Удаляем старые линии
    const oldProgressLine = container.querySelector('.timeline__progress-line');
    const oldDashedLine = container.querySelector('.timeline__dashed-line');
    if (oldProgressLine) oldProgressLine.remove();
    if (oldDashedLine) oldDashedLine.remove();
    
    if (items.length === 0) return;
    
    // Вычисляем высоту до последнего урока
    const lastItem = items[items.length - 1];
    const firstItem = items[0];
    const containerRect = container.getBoundingClientRect();
    const lastItemRect = lastItem.getBoundingClientRect();
    const firstItemRect = firstItem.getBoundingClientRect();
    
    // Точка находится на top: 20px + 7px (центр точки)
    const dotCenterOffset = 20 + 7;
    const lineStartY = (firstItemRect.top - containerRect.top) + dotCenterOffset;
    const lineEndY = (lastItemRect.top - containerRect.top) + dotCenterOffset;
    const totalLineHeight = lineEndY - lineStartY;
    
    // Создаём пунктирную линию (от первой до последней точки)
    if (totalLineHeight > 0) {
        const dashedLine = document.createElement('div');
        dashedLine.className = 'timeline__dashed-line';
        dashedLine.style.top = `${lineStartY}px`;
        dashedLine.style.height = `${totalLineHeight}px`;
        container.insertBefore(dashedLine, container.firstChild);
    }
    
    // Если нет пройденных уроков, не рисуем линию прогресса
    if (completedCount === 0) return;
    
    // Находим последний пройденный урок
    let lastCompletedIndex = -1;
    items.forEach((item, index) => {
        if (item.classList.contains('timeline__item--completed')) {
            lastCompletedIndex = index;
        }
    });
    
    if (lastCompletedIndex === -1) return;
    
    // Вычисляем высоту линии прогресса
    const lastCompletedItem = items[lastCompletedIndex];
    const lastCompletedRect = lastCompletedItem.getBoundingClientRect();
    const progressEndY = (lastCompletedRect.top - containerRect.top) + dotCenterOffset;
    const progressHeight = progressEndY - lineStartY;
    
    if (progressHeight > 0) {
        const progressLine = document.createElement('div');
        progressLine.className = 'timeline__progress-line';
        progressLine.style.top = `${lineStartY}px`;
        progressLine.style.height = `${progressHeight}px`;
        container.insertBefore(progressLine, container.firstChild);
    }
}

// Запуск
loadTimeline();
