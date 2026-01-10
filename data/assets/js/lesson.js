// Инициализация WebApp
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand(); // Раскрыть на весь экран
}

// Получаем параметры из URL
function getUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    return {
        slug: urlParams.get('slug'),
        telegramId: urlParams.get('telegram_id')
    };
}

// Получаем ID пользователя
function getTelegramId() {
    const params = getUrlParams();
    
    if (params.telegramId) {
        return params.telegramId;
    }
    
    // Пробуем получить из Telegram WebApp
    if (tg?.initDataUnsafe?.user?.id) {
        return String(tg.initDataUnsafe.user.id);
    }
    
    // Заглушка для тестов
    return "123456789";
}

const params = getUrlParams();
const lessonSlug = params.slug;
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
const COMPLETE_API_URL = `${API_BASE_URL}/api/v1/course/complete`;

// Мок-данные для контента урока (в продакшене это будет загружаться через API)
const mockLessonContent = {
    'intro': {
        title: 'Introduction to Clay',
        video: 'https://example.com/video1.mp4',
        text: `
            <p>Добро пожаловать в курс по керамике! В этом первом уроке мы познакомимся с основами работы с глиной.</p>
            <p>Глина — это природный материал, который использовался людьми на протяжении тысячелетий для создания различных предметов.</p>
            <p>Мы изучим основные типы глины, их свойства и способы подготовки к работе.</p>
        `,
        image: 'https://example.com/image1.jpg'
    },
    'centering': {
        title: 'Centering on the Wheel',
        video: 'https://example.com/video2.mp4',
        text: `
            <p>Центрирование глины на гончарном круге — это фундаментальный навык, который необходимо освоить каждому керамисту.</p>
            <p>В этом уроке вы узнаете правильную технику центрирования и потренируетесь на практике.</p>
            <p>Мы разберем основные ошибки новичков и способы их избежать.</p>
        `,
        image: 'https://example.com/image2.jpg'
    },
    'glazing': {
        title: 'Glazing Basics',
        video: 'https://example.com/video3.mp4',
        text: `
            <p>Глазурование — это финальный этап создания керамического изделия, который придает ему красивый внешний вид и защиту.</p>
            <p>Вы узнаете о различных типах глазурей, способах их нанесения и обжиге.</p>
            <p>Мы также рассмотрим цветовые решения и техники декорирования.</p>
        `,
        image: 'https://example.com/image3.jpg'
    }
};

// Загрузка контента урока
function loadLessonContent() {
    if (!lessonSlug) {
        showError('Урок не найден');
        return;
    }

    // Получаем контент (пока из мок-данных, в продакшене будет API)
    const content = mockLessonContent[lessonSlug] || {
        title: 'Урок',
        video: '',
        text: '<p>Контент урока загружается...</p>',
        image: ''
    };

    // Обновляем заголовок
    const titleElement = document.getElementById('lesson-title');
    if (titleElement) {
        titleElement.textContent = content.title;
    }

    // Обновляем видео (пока плейсхолдер)
    const videoElement = document.getElementById('lesson-video');
    if (videoElement) {
        if (content.video) {
            videoElement.innerHTML = `
                <video width="100%" height="100%" controls style="border-radius: 12px;">
                    <source src="${content.video}" type="video/mp4">
                    Ваш браузер не поддерживает видео.
                </video>
            `;
        } else {
            videoElement.textContent = 'Видео будет здесь';
        }
    }

    // Обновляем текст
    const textElement = document.getElementById('lesson-text');
    if (textElement) {
        textElement.innerHTML = content.text;
    }

    // Обновляем изображение (пока плейсхолдер)
    const imageElement = document.getElementById('lesson-image');
    if (imageElement) {
        if (content.image) {
            imageElement.innerHTML = `<img src="${content.image}" alt="${content.title}" style="width: 100%; height: 100%; object-fit: cover; border-radius: 12px;">`;
        } else {
            imageElement.textContent = 'Изображение будет здесь';
        }
    }

    // Обновляем ссылку "Назад"
    const backLink = document.getElementById('back-link');
    if (backLink) {
        backLink.href = `index.html?telegram_id=${encodeURIComponent(telegramId)}`;
    }
}

// Завершение урока
async function completeLesson() {
    const completeBtn = document.getElementById('complete-btn');
    
    if (!completeBtn || !lessonSlug) {
        return;
    }

    // Блокируем кнопку
    completeBtn.disabled = true;
    completeBtn.textContent = 'Отправка...';

    try {
        const response = await fetch(COMPLETE_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                telegram_id: telegramId,
                lesson_slug: lessonSlug
            })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            // Успех: анимация и редирект
            completeBtn.classList.add('lesson-page__complete-btn--success');
            completeBtn.textContent = '✓ Урок завершен!';
            
            // Редирект через 1 секунду
            setTimeout(() => {
                window.location.href = `index.html?telegram_id=${encodeURIComponent(telegramId)}`;
            }, 1000);
        } else {
            // Ошибка
            showError(data.message || 'Не удалось завершить урок');
            completeBtn.disabled = false;
            completeBtn.textContent = 'Завершить урок';
        }
    } catch (error) {
        console.error('Ошибка завершения урока:', error);
        showError('Ошибка соединения. Попробуйте еще раз.');
        completeBtn.disabled = false;
        completeBtn.textContent = 'Завершить урок';
    }
}

function showError(message) {
    const contentElement = document.querySelector('.lesson-page__content');
    if (contentElement) {
        contentElement.innerHTML = `<p style="color: var(--color-accent); padding: 20px;">${message}</p>`;
    }
}

// Инициализация
document.addEventListener('DOMContentLoaded', () => {
    loadLessonContent();

    // Обработчик кнопки завершения
    const completeBtn = document.getElementById('complete-btn');
    if (completeBtn) {
        completeBtn.addEventListener('click', completeLesson);
    }
});
