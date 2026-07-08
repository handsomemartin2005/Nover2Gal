from __future__ import annotations


def infer_background_key(text: str) -> str:
    location = infer_stage(text).get("location")
    return background_key_for_location(location)


def background_key_for_location(location: str) -> str:
    location = canonical_location(location)
    if location == "home_living":
        return "bg_home_living"
    if location == "restaurant":
        return "bg_restaurant"
    if location == "bedroom":
        return "bg_bedroom"
    if location == "kitchen":
        return "bg_kitchen"
    if location == "office":
        return "bg_office"
    if location == "village":
        return "bg_village"
    if location == "field":
        return "bg_field"
    if location == "yard":
        return "bg_yard"
    if location == "cave_dwelling":
        return "bg_cave_dwelling"
    if location == "station":
        return "bg_station"
    if location == "hospital":
        return "bg_hospital"
    if location == "shop":
        return "bg_shop"
    if location == "bathroom":
        return "bg_bathroom"
    if location == "toilet":
        return "bg_toilet"
    if location == "dormitory":
        return "bg_dormitory"
    if location == "school_hallway":
        return "bg_school_hallway"
    if location == "rooftop":
        return "bg_rooftop"
    if location == "street":
        return "bg_street"
    if location == "classroom":
        return "bg_classroom"
    if location == "old_school":
        return "bg_old_school_night"
    return "bg_default"


def canonical_location(location: str) -> str:
    normalized = (location or "generic").strip().lower()
    aliases = {
        "home": "home_living",
        "living": "home_living",
        "living_room": "home_living",
        "room": "bedroom",
        "home_bedroom": "bedroom",
        "hotel_room": "bedroom",
        "school_rooftop": "rooftop",
        "roof": "rooftop",
        "roof_top": "rooftop",
        "corridor": "school_hallway",
        "hallway": "school_hallway",
        "school_corridor": "school_hallway",
        "restroom": "toilet",
        "washroom": "toilet",
        "lavatory": "toilet",
        "pool_cafe": "restaurant",
        "cafe": "restaurant",
        "hotel_pool": "restaurant",
        "pool": "restaurant",
        "shopping_mall": "shop",
        "shopping_mall_entrance": "shop",
        "mall": "shop",
        "bookstore": "shop",
        "old_school_night": "old_school",
        "station_platform": "station",
        "train_platform": "station",
        "bus_platform": "station",
        "hotel_bathroom": "bathroom",
    }
    return aliases.get(normalized, normalized)


def infer_stage(text: str, character_names: list[str] | None = None) -> dict:
    props: set[str] = set()
    characters: set[str] = set()

    if any(term in text for term in ["浴室", "浴缸", "洗澡", "淋浴", "澡堂"]):
        location = "bathroom"
        props.update(["bath", "mirror", "towel"])
    elif any(term in text for term in ["女厕", "男厕", "厕所", "卫生间", "洗手间"]):
        location = "toilet"
        props.update(["sink", "mirror", "door"])
    elif any(term in text for term in ["宿舍", "寝室", "上下铺"]):
        location = "dormitory"
        props.update(["bed", "desk", "wardrobe"])
    elif any(term in text for term in ["天台", "楼顶", "屋顶", "顶楼"]):
        location = "rooftop"
        props.update(["fence", "sky", "door"])
    elif any(term in text for term in ["学校走廊", "教学楼走廊", "走廊", "楼道"]):
        location = "school_hallway"
        props.update(["corridor", "window", "door"])
    elif any(term in text for term in ["卧室", "床边", "床上"]):
        location = "bedroom"
        props.update(["bed", "wardrobe", "lamp"])
    elif any(term in text for term in ["厨房", "灶台", "锅", "碗柜"]):
        location = "kitchen"
        props.update(["counter", "stove", "bowl"])
    elif any(term in text for term in ["办公室", "书房", "办公桌"]):
        location = "office"
        props.update(["desk", "bookshelf", "lamp"])
    elif any(term in text for term in ["医院", "病房", "诊所", "医生", "护士"]):
        location = "hospital"
        props.update(["bed", "curtain", "chair", "lamp"])
    elif any(term in text for term in ["商店", "小卖部", "供销社", "柜台", "货架"]):
        location = "shop"
        props.update(["counter", "shelf", "sign"])
    elif any(term in text for term in ["车站", "站台", "候车", "汽车站", "火车站"]):
        location = "station"
        props.update(["bench", "sign", "road"])
    elif any(term in text for term in ["窑洞", "土炕", "炕上"]):
        location = "cave_dwelling"
        props.update(["kang", "table", "stove", "cup"])
    elif any(term in text for term in ["院子", "院里", "院门", "门槛"]):
        location = "yard"
        props.update(["tree", "fence", "door", "bench"])
    elif any(term in text for term in ["田", "地里", "庄稼", "山坡", "麦", "玉米", "劳动"]):
        location = "field"
        props.update(["field", "tree", "road"])
    elif any(term in text for term in ["村", "庄", "村口", "乡下"]):
        location = "village"
        props.update(["tree", "fence", "road"])
    elif any(term in text for term in ["街", "路上", "车站", "巷"]):
        location = "street"
        props.update(["road", "streetlight", "sign"])
    elif any(term in text for term in ["家", "会客", "客厅", "屋里", "房间"]):
        location = "home_living"
        props.update(["sofa", "table", "chair"])
    elif any(term in text for term in ["饭店", "餐厅", "饭馆", "吃饭"]):
        location = "restaurant"
        props.update(["table", "chair", "bowl"])
    elif any(term in text for term in ["教室", "讲台", "课桌", "黑板"]):
        location = "classroom"
        props.update(["blackboard", "desk", "chair"])
    elif any(term in text for term in ["旧教学楼", "教学楼", "走廊"]):
        location = "old_school"
        props.update(["windows", "corridor", "door"])
    else:
        location = "generic"
        props.add("floor")

    if "桌" in text:
        props.add("table")
    if "椅" in text:
        props.add("chair")
    if "床" in text:
        props.add("bed")
    if any(term in text for term in ["柜", "书柜", "衣柜"]):
        props.add("bookshelf" if "书" in text else "wardrobe")
    if any(term in text for term in ["货架", "架子"]):
        props.add("shelf")
    if "书" in text:
        props.add("book")
    if any(term in text for term in ["纸条", "纸", "信"]):
        props.add("paper")
    if any(term in text for term in ["灯", "台灯"]):
        props.add("lamp")
    if "手机" in text or "电话" in text:
        props.add("phone")
    if "书包" in text or "包" in text:
        props.add("bag")
    if "衣" in text or "衣服" in text:
        props.add("clothes")
    if "伞" in text:
        props.add("umbrella")
    if "煤" in text or "煤油灯" in text:
        props.add("lamp")
    if "锅" in text:
        props.add("stove")
    if any(term in text for term in ["杯", "茶"]):
        props.add("cup")
    if "门" in text:
        props.add("door")
    if "窗" in text:
        props.add("window")
    if any(term in text for term in ["镜", "镜子"]):
        props.add("mirror")
    if any(term in text for term in ["毛巾", "浴巾"]):
        props.add("towel")
    if any(term in text for term in ["水池", "洗手台", "洗脸池"]):
        props.add("sink")
    if any(term in text for term in ["浴缸", "澡盆"]):
        props.add("bath")
    if any(term in text for term in ["长凳", "板凳", "凳子"]):
        props.add("bench")
    if any(term in text for term in ["炕", "土炕"]):
        props.add("kang")
    if any(term in text for term in ["柜台", "灶台"]):
        props.add("counter")
    if any(term in text for term in ["田", "地里", "庄稼", "麦", "玉米"]):
        props.add("field")
    if any(term in text for term in ["雨", "雨声", "下雨", "暴雨"]):
        props.add("weather_rain")
    if any(term in text for term in ["雪", "下雪"]):
        props.add("weather_snow")
    if any(term in text for term in ["晴", "太阳", "日头"]):
        props.add("weather_sun")
    if any(term in text for term in ["风", "刮风"]):
        props.add("weather_wind")
    if any(term in text for term in ["狗", "犬"]):
        props.add("animal_dog")
    if "猫" in text:
        props.add("animal_cat")
    if any(term in text for term in ["鸡", "公鸡", "母鸡"]):
        props.add("animal_chicken")
    if "牛" in text:
        props.add("animal_cow")
    if any(term in text for term in ["马匹", "马儿", "马车", "骑马", "牵马", "骡"]):
        props.add("animal_horse")
    if "羊" in text:
        props.add("animal_sheep")

    if "主人公" in text:
        characters.add("protagonist")
    for name in character_names or []:
        if name and name in text:
            characters.add(name)
    if not characters:
        characters.add("protagonist")

    return {
        "location": canonical_location(location),
        "props": sorted(props),
        "characters": sorted(characters),
    }
