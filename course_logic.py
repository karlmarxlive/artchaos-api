def calculate_timeline(all_lessons: list, user_progress: dict) -> list[dict]:
    """
    Превращает сырые данные в красивый список для фронтенда.
    Определяет статусы: completed, active, locked.
    """
    timeline = []
    
    access_blocks_str = user_progress.get("Access Blocks", "")
    allowed_blocks = [b.strip() for b in access_blocks_str.split(",") if b.strip()]
    
    completed_list = user_progress.get("Completed_Lessons", [])
    completed_slugs = set()
    for item in completed_list:
        if isinstance(item, dict):
            completed_slugs.add(item.get("Slug"))
        else:
            pass

    found_active = False
    
    last_block = None

    for lesson in all_lessons:
        if lesson.get("Block ID") not in allowed_blocks:
            continue
            
        slug = lesson.get("Slug")
        is_completed = slug in completed_slugs
        
        if is_completed:
            status = "completed"
        elif not found_active:
            status = "active"
            found_active = True
        else:
            status = "locked"
            
        # Формируем объект для фронтенда
        timeline_item = {
            "slug": slug,
            "title": lesson.get("Title"),
            "status": status,
            "is_new_block": lesson.get("Block ID") != last_block,
            "block_id": lesson.get("Block ID"),
            "system_id": lesson.get("Id") 
        }
        
        timeline.append(timeline_item)
        last_block = lesson.get("Bloc ID")
        
    return timeline