def calculate_timeline(all_lessons: list, user_progress: dict) -> list[dict]:
    """
    Превращает сырые данные в красивый список для фронтенда.
    Определяет статусы: completed, active, locked.
    """
    timeline = []
    
    import logging
    logger = logging.getLogger(__name__)
    
    access_blocks_str = user_progress.get("Access Blocks", "")
    allowed_blocks = [b.strip() for b in access_blocks_str.split(",") if b.strip()]
    
    # Пробуем разные варианты имени поля для пройденных уроков
    completed_list = (
        user_progress.get("Completed_Lessons") or 
        user_progress.get("Completed Lessons") or 
        user_progress.get("completed_lessons") or 
        []
    )
    
    completed_slugs = set()
    
    # Логируем для отладки
    logger.info(f"user_progress keys: {list(user_progress.keys())}")
    logger.info(f"Completed_Lessons из user_progress: {completed_list}, тип: {type(completed_list)}")
    
    # Обрабатываем список пройденных уроков
    if completed_list:
        # Если это список словарей (правильный формат)
        if isinstance(completed_list, list):
            for item in completed_list:
                if isinstance(item, dict):
                    # Если это словарь, извлекаем Slug
                    slug = item.get("Slug") or item.get("slug")
                    if slug:
                        completed_slugs.add(str(slug))
                        logger.debug(f"Добавлен пройденный урок: {slug}")
                elif isinstance(item, (str, int)):
                    # Если это строка или число (возможно, ID урока), нужно найти slug по ID
                    # Ищем урок по ID в all_lessons
                    for lesson in all_lessons:
                        if str(lesson.get("Id")) == str(item):
                            slug = lesson.get("Slug")
                            if slug:
                                completed_slugs.add(str(slug))
                                logger.debug(f"Добавлен пройденный урок по ID {item}: {slug}")
                            break
        # Если это словарь (редкий случай - один урок)
        elif isinstance(completed_list, dict):
            slug = completed_list.get("Slug") or completed_list.get("slug")
            if slug:
                completed_slugs.add(str(slug))
        # Если это число - это означает, что данные не загрузились правильно
        # (должно быть исправлено в nocodb_client, но на всякий случай логируем)
        elif isinstance(completed_list, (int, float)):
            logger.warning(f"Completed_Lessons является числом ({completed_list}), а не списком. Данные должны быть загружены через links API.")
    
    logger.info(f"Извлеченные completed_slugs: {completed_slugs}")
    logger.info(f"Всего уроков: {len(all_lessons)}, пройдено: {len(completed_slugs)}")

    found_active = False
    
    last_block = None

    for lesson in all_lessons:
        lesson_block_id = lesson.get("Block ID")
        
        # Пропускаем уроки с пустым или NULL Block ID
        if not lesson_block_id or lesson_block_id == "NULL" or str(lesson_block_id).strip() == "":
            logger.debug(f"Пропущен урок {lesson.get('Slug')} с пустым Block ID")
            continue
        
        has_access = lesson_block_id in allowed_blocks
        
        slug = lesson.get("Slug")
        is_completed = slug in completed_slugs
        
        logger.debug(f"Урок {slug}: is_completed={is_completed}, found_active={found_active}, has_access={has_access}, block_id={lesson_block_id}")
        
        # Если у пользователя нет доступа к блоку, урок всегда locked
        if not has_access:
            status = "locked"
        elif is_completed:
            # Урок пройден
            status = "completed"
        elif not found_active:
            # Это первый непройденный урок из доступного блока - делаем его активным
            status = "active"
            found_active = True
        else:
            # Урок из доступного блока, но есть более ранний непройденный урок
            status = "locked"
        
        logger.debug(f"Урок {slug}: установлен статус {status}")
            
        # Формируем объект для фронтенда
        timeline_item = {
            "slug": slug,
            "title": lesson.get("Title"),
            "status": status,
            "is_new_block": lesson_block_id != last_block,
            "block_id": lesson_block_id,
            "system_id": lesson.get("Id") 
        }
        
        timeline.append(timeline_item)
        last_block = lesson_block_id
        
    return timeline