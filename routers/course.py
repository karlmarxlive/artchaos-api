from fastapi import APIRouter
import nocodb_client
import course_logic
import schemas


router = APIRouter(
    prefix="/api/v1/course",
    tags=["Course"]
)


@router.get("/timeline")
async def get_course_timeline(telegram_id: str):
    """
    Возвращает структуру курса с учетом прогресса.
    """
    user_progress = await nocodb_client.get_user_course_progress(telegram_id)
    
    if not user_progress:
        await nocodb_client.create_user_progress(telegram_id, default_blocks="1")
        user_progress = await nocodb_client.get_user_course_progress(telegram_id)

    if not user_progress:
        return {
            "status": "error",
            "message": "Не удалось инициализировать прогресс пользователя. Проверь логи сервера."
        }
    
    all_lessons = await nocodb_client.get_all_lessons()

    if not all_lessons:
         return {
            "status": "error",
            "message": "Список уроков пуст или недоступен."
        }
    
    timeline_data = course_logic.calculate_timeline(all_lessons, user_progress)
    
    return {
        "status": "success",
        "timeline": timeline_data,
        "user_name": user_progress.get("Telegram ID")
    }


@router.post("/complete")
async def complete_lesson(data: schemas.LessonCompleteRequest):
    """
    Отмечает урок как пройденный.
    """
    all_lessons = await nocodb_client.get_all_lessons()
    lesson_db_id = None
    
    for lesson in all_lessons:
        if lesson.get("Slug") == data.lesson_slug:
            lesson_db_id = lesson.get("Id")
            break
            
    if not lesson_db_id:
        return {"status": "error", "message": "Урок не найден"}
        
    success = await nocodb_client.mark_lesson_as_completed(data.telegram_id, lesson_db_id)
    
    if success:
        return {"status": "success"}
    else:
        return {"status": "error", "message": "Не удалось сохранить прогресс"}