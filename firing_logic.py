# Словарь цен на обжиг (сама работа)
# Размер -> Тип обжига -> Цена
FIRING_PRICES = {
    "микро": {
        "утель": 15,
        "глазурь до 1120": 20,
        "глазурь до 1220": 25
    },
    "маленькое": {
        "утель": 60,
        "глазурь до 1120": 100,
        "глазурь до 1220": 130
    },
    "среднее": {
        "утель": 150,
        "глазурь до 1120": 180,
        "глазурь до 1220": 220
    },
    "большое": {
        "утель": 200,
        "глазурь до 1120": 240,
        "глазурь до 1220": 280
    }
}

# Словарь цен на глазурь из мастерской (доплата)
# Размер -> Тип обжига -> Цена
WORKSHOP_GLAZE_PRICES = {
    "микро": {
        "глазурь до 1120": 25,
        "глазурь до 1220": 35
    },
    "маленькое": {
        "глазурь до 1120": 100,
        "глазурь до 1220": 130
    },
    "среднее": {
        "глазурь до 1120": 180,
        "глазурь до 1220": 220
    },
    "большое": {
        "глазурь до 1120": 240,
        "глазурь до 1220": 280
    }
}

def calculate_base_item_cost(size: str, firing_type: str, glaze_type: str) -> int:
    """
    Считает стоимость ОДНОГО изделия без учета скидок клиента.
    Возвращает цену или -1, если параметры неверны.
    """
    size = size.lower()
    firing_type = firing_type.lower()
    glaze_type = glaze_type.lower()

    size_prices = FIRING_PRICES.get(size)
    if not size_prices:
        return -1
    
    base_cost = size_prices.get(firing_type)
    if base_cost is None:
        return -1

    glaze_surcharge = 0
    if glaze_type == "из мастерской":
        if firing_type == "утель":
            glaze_surcharge = 0
        else:
            glaze_prices = WORKSHOP_GLAZE_PRICES.get(size)
            if glaze_prices:
                glaze_surcharge = glaze_prices.get(firing_type, 0)

    return base_cost + glaze_surcharge