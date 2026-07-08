from __future__ import annotations

import re


def build_concrete_choice_block(scene_id: str, source_text: str) -> dict:
    concrete = concrete_scene_anchor(source_text)
    choice_pair = daily_choice_pair(concrete, scene_id)
    mainline = _normalize_choice_texts(choice_pair["mainline"], add_aside=True)
    divergent = _normalize_choice_texts(choice_pair["divergent"], add_aside=True)
    return {
        "type": "choice",
        "choice_mode": choice_pair["choice_mode"],
        "choices": [
            {
                "text": mainline["text"],
                "route": "mainline",
                "branch_text": mainline["branch_text"],
                "converge_text": mainline["converge_text"],
                "effects": {"flag_followed_scene_action": True},
                "next_label": f"{scene_id}_follow",
            },
            {
                "text": divergent["text"],
                "route": "divergent",
                "branch_text": divergent["branch_text"],
                "converge_text": divergent["converge_text"],
                "effects": {divergent["flag"]: True},
                "next_label": f"{scene_id}_{divergent['suffix']}",
            },
        ],
    }


def concrete_scene_anchor(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "眼前的局面还没有结束"
    question = _question_anchor(cleaned)
    if question:
        return question
    sentences = [part.strip(" ，,。！？!?；;") for part in re.split(r"[。！？!?；;\n]", cleaned) if part.strip()]
    if not sentences:
        return cleaned[:36]
    scored = sorted(sentences, key=lambda item: (_action_score(item), -len(item)), reverse=True)
    return scored[0][:42]


def daily_choice_pair(anchor: str, scene_id: str) -> dict:
    if any(term in anchor for term in ["披萨", "汉堡", "咖啡", "面", "饭", "菜单", "点菜", "晚饭", "饭店", "餐厅", "饭馆", "吃"]):
        return food_choice_pair(anchor)
    if any(term in anchor for term in ["同意", "答应", "拒绝", "不同意", "愿意", "要不要", "可以不可以", "行不行"]):
        return agreement_choice_pair(anchor)
    if any(term in anchor for term in ["喜欢", "爱", "表白", "心意"]):
        return feeling_choice_pair(anchor)
    if any(term in anchor for term in ["A", "B", "C", "D", "选项", "选择", "答案"]):
        return answer_choice_pair(anchor)
    if any(term in anchor for term in ["纸条", "纸", "信", "字条", "藏"]):
        return paper_choice_pair(anchor)
    if any(term in anchor for term in ["钱", "借", "还钱", "工钱", "工资"]):
        return money_choice_pair(anchor)
    if any(term in anchor for term in ["帮", "帮忙", "照顾", "送", "拿给"]):
        return help_choice_pair(anchor)
    if any(term in anchor for term in ["门", "走", "停", "回家", "留下", "出去", "进去", "离开"]):
        return movement_choice_pair(anchor)
    if _has_question(anchor):
        return question_choice_pair(anchor, scene_id)
    if any(term in anchor for term in ["问", "说", "告诉", "解释", "开口"]):
        return talk_choice_pair(anchor, scene_id)
    return generic_daily_choice_pair(anchor, scene_id)


def question_choice_pair(anchor: str, scene_id: str) -> dict:
    if any(term in anchor for term in ["帮", "帮忙", "能不能", "可不可以"]):
        return {
            "choice_mode": "opposed",
            "mainline": {
                "text": "答应帮忙",
                "branch_text": "我点头答应，先把她眼前的难处接过来。",
                "converge_text": "事情有了着落，她才继续把后面的话说完。",
            },
            "divergent": {
                "text": "说还得想想",
                "branch_text": "我没有立刻答应，只把顾虑摊开说清。",
                "converge_text": "她沉默了一会儿，最后还是把话题拉回眼前。",
                "flag": "flag_hesitated_help",
                "suffix": "hesitate_help",
            },
        }
    if any(term in anchor for term in ["去哪", "去不去", "走不走", "要不要走"]):
        return movement_choice_pair(anchor)
    variants = [
        {
            "choice_mode": "opposed",
            "mainline": ("实话回答", "我把知道的事说出来，没有再绕弯。", "对方听完以后，又问到最关键的地方。"),
            "divergent": ("先含糊过去", "我把话停在半路，只给了一个不太确定的回答。", "这句话没有糊弄太久，问题还是回到眼前。", "flag_vague_answer", "vague_answer"),
        },
        {
            "choice_mode": "opposed",
            "mainline": ("点头承认", "我轻轻点头，承认她刚才说中了。", "她看了我一会儿，才继续往下说。"),
            "divergent": ("轻轻摇头", "我摇了摇头，没有顺着她的判断接下去。", "她皱了下眉，但谈话还是没有断。", "flag_denied_once", "deny_once"),
        },
        {
            "choice_mode": "parallel",
            "mainline": ("反问一句", "我没有马上回答，先把问题递回去。", "她被问得停了一下，还是把话接住了。"),
            "divergent": ("低声回答", "我压低声音，把答案说得只够她听见。", "周围安静下来，刚才的问题继续往下压。", "flag_low_voice_answer", "low_voice"),
        },
        {
            "choice_mode": "opposed",
            "mainline": ("把话说透", "我把没说完的半句补完整，不再留余地。", "话说出口以后，屋里的气氛明显变了。"),
            "divergent": ("只说一半", "我把后半句话咽回去，只留一个模糊的说法。", "她没有立刻逼问，但眼神已经变得认真。", "flag_half_answer", "half_answer"),
        },
    ]
    variant = variants[_stable_index(anchor + scene_id, len(variants))]
    mainline = variant["mainline"]
    divergent = variant["divergent"]
    return {
        "choice_mode": variant["choice_mode"],
        "mainline": {"text": mainline[0], "branch_text": mainline[1], "converge_text": mainline[2]},
        "divergent": {
            "text": divergent[0],
            "branch_text": divergent[1],
            "converge_text": divergent[2],
            "flag": divergent[3],
            "suffix": divergent[4],
        },
    }


def food_choice_pair(anchor: str) -> dict:
    if "披萨" in anchor:
        return {
            "choice_mode": "parallel",
            "mainline": {
                "text": "吃披萨",
                "branch_text": "你照着原先说好的，点了那份披萨。",
                "converge_text": "饭吃完后，你们还是一起离开座位。",
            },
            "divergent": {
                "text": "改吃汉堡",
                "branch_text": "你把菜单翻回去，临时换成了汉堡。",
                "converge_text": "这顿饭没有耽误太久，吃完后你们还是出了门。",
                "flag": "flag_changed_food",
                "suffix": "burger",
            },
        }
    return {
        "choice_mode": "parallel",
        "mainline": {
            "text": "按她说的点",
            "branch_text": "你把菜单递回去，照她刚才说的点了菜。",
            "converge_text": "菜上齐以后，你们还是坐回同一张桌边。",
        },
        "divergent": {
            "text": "换一道菜",
            "branch_text": "你指了指菜单另一页，换成自己更想吃的那道。",
            "converge_text": "小小的改动没有打断谈话，饭桌上的话题又接了回来。",
            "flag": "flag_changed_dish",
            "suffix": "dish",
        },
    }


def agreement_choice_pair(anchor: str) -> dict:
    target = "她" if "她" in anchor or "女" in anchor or "苏晚" in anchor else "对方"
    return {
        "choice_mode": "opposed",
        "mainline": {
            "text": f"答应{target}",
            "branch_text": f"你点了点头，先按{target}的意思来。",
            "converge_text": f"{target}的语气缓下来，话题继续往下走。",
        },
        "divergent": {
            "text": "先拒绝",
            "branch_text": "你摇了摇头，把自己的顾虑说出来。",
            "converge_text": "短暂僵住以后，你们还是得把眼前的事说清。",
            "flag": "flag_refused_once",
            "suffix": "refuse",
        },
    }


def feeling_choice_pair(anchor: str) -> dict:
    target = "她" if "她" in anchor or "苏晚" in anchor or "女" in anchor else "对方"
    return {
        "choice_mode": "opposed",
        "mainline": {
            "text": f"承认喜欢{target}",
            "branch_text": "你把话说出口，没有再用玩笑遮过去。",
            "converge_text": "短暂的安静后，你们还是面对了眼前的问题。",
        },
        "divergent": {
            "text": "先不说出口",
            "branch_text": "你把那句话咽了回去，只换成一句普通的回应。",
            "converge_text": "她没有追问，谈话仍然回到刚才的事情上。",
            "flag": "flag_hid_feeling",
            "suffix": "hide_feeling",
        },
    }


def answer_choice_pair(anchor: str) -> dict:
    return {
        "choice_mode": "parallel",
        "mainline": {
            "text": "选择A",
            "branch_text": "你把答案停在A上，没有再改。",
            "converge_text": "选择落定后，接下来的安排照常推进。",
        },
        "divergent": {
            "text": "选择D",
            "branch_text": "你把手移到D上，临时改了主意。",
            "converge_text": "这个选择只带来一点波澜，事情仍然继续往下走。",
            "flag": "flag_chose_d",
            "suffix": "choose_d",
        },
    }


def paper_choice_pair(anchor: str) -> dict:
    return {
        "choice_mode": "parallel",
        "mainline": {
            "text": "把纸条拿过来",
            "branch_text": "你伸手把纸条拿到灯下，看清上面的字。",
            "converge_text": "纸条的事没有过去，她的目光仍停在你手边。",
        },
        "divergent": {
            "text": "让她先收起来",
            "branch_text": "你没有去抢，只看着她把纸条压回身后。",
            "converge_text": "她避开了一下，但纸条仍然成了你们绕不开的话题。",
            "flag": "flag_let_paper_go",
            "suffix": "paper_wait",
        },
    }


def money_choice_pair(anchor: str) -> dict:
    return {
        "choice_mode": "opposed",
        "mainline": {
            "text": "把钱递过去",
            "branch_text": "你把钱数好递过去，没有再多问。",
            "converge_text": "钱收下以后，话题又落回刚才那件事。",
        },
        "divergent": {
            "text": "先问清用途",
            "branch_text": "你把钱按在手里，问这笔钱到底要做什么。",
            "converge_text": "对方避不开这个问题，只能把话继续说下去。",
            "flag": "flag_asked_money_use",
            "suffix": "money_ask",
        },
    }


def help_choice_pair(anchor: str) -> dict:
    return {
        "choice_mode": "opposed",
        "mainline": {
            "text": "过去帮忙",
            "branch_text": "你走过去接过她手里的东西，先帮她把事做完。",
            "converge_text": "东西放稳以后，你们又回到刚才的话头。",
        },
        "divergent": {
            "text": "让她自己来",
            "branch_text": "你没有立刻伸手，只提醒她小心一点。",
            "converge_text": "她自己处理完以后，还是抬头看向你。",
            "flag": "flag_did_not_help",
            "suffix": "no_help",
        },
    }


def movement_choice_pair(anchor: str) -> dict:
    if "回家" in anchor:
        main_text = "一起回家"
        branch_text = "你跟上她的脚步，沿着原路往家里走。"
        converge_text = "路上的沉默没有拖太久，你们还是说回刚才的事。"
        divergent_text = "再待一会儿"
        divergent_branch = "你停在原地，想再多看一眼周围。"
        divergent_converge = "多待的这一会儿没有改变结果，你们最终还是往回走。"
    elif any(term in anchor for term in ["出去", "离开", "走"]):
        main_text = "跟着出去"
        branch_text = "你跟着她出了门，外面的声音一下子近了。"
        converge_text = "走出几步后，你们还是绕不开刚才的话题。"
        divergent_text = "先留下来"
        divergent_branch = "你没有马上动，只在原地多停了一会儿。"
        divergent_converge = "等她回头看你，你还是迈步跟了上去。"
    else:
        main_text = "推门进去"
        branch_text = "你握住门把，把门推开走了进去。"
        converge_text = "门后的动静慢慢清楚，你们都回到这件事面前。"
        divergent_text = "先留在门口"
        divergent_branch = "你没有立刻进去，只站在门口听里面的声音。"
        divergent_converge = "等那阵声音过去，你还是推开了门。"
    return {
        "choice_mode": "opposed",
        "mainline": {"text": main_text, "branch_text": branch_text, "converge_text": converge_text},
        "divergent": {
            "text": divergent_text,
            "branch_text": divergent_branch,
            "converge_text": divergent_converge,
            "flag": "flag_waited_or_left",
            "suffix": "movement_alt",
        },
    }


def talk_choice_pair(anchor: str, scene_id: str) -> dict:
    variants = [
        {
            "choice_mode": "opposed",
            "mainline": ("直接开口问", "你没有绕弯，把问题直接问出口。", "她的反应慢了一拍，谈话没有就此结束。"),
            "divergent": ("先换个话题", "你把问题压下去，先提起一件不那么紧的事。", "话题绕了一圈，还是回到刚才那个问题。", "flag_changed_topic", "change_topic"),
        },
        {
            "choice_mode": "parallel",
            "mainline": ("把水递过去", "你把杯子推到她手边，让她先缓一口气。", "她握住杯子，终于把话接了下去。"),
            "divergent": ("把窗关上", "你先走到窗边，把外面的声响隔在屋外。", "屋里安静下来，刚才没说完的话又回来了。", "flag_closed_window", "close_window"),
        },
        {
            "choice_mode": "opposed",
            "mainline": ("帮她收拾东西", "你弯腰把散在桌边的东西拢到一起。", "东西收好后，她没有再躲开你的视线。"),
            "divergent": ("先站着不动", "你没有伸手，只等她自己把东西收好。", "她动作慢了些，最后还是开了口。", "flag_waited_to_help", "wait_help"),
        },
        {
            "choice_mode": "parallel",
            "mainline": ("跟着她走", "你跟上她的脚步，没有在门口停太久。", "走出几步后，她把刚才的话补完整。"),
            "divergent": ("留在原地听", "你停在原地，先听清周围有没有别的动静。", "确认没有人靠近后，你们又说回刚才的事。", "flag_listened_first", "listen_first"),
        },
    ]
    variant = variants[_stable_index(anchor + scene_id, len(variants))]
    mainline = variant["mainline"]
    divergent = variant["divergent"]
    return {
        "choice_mode": variant["choice_mode"],
        "mainline": {"text": mainline[0], "branch_text": mainline[1], "converge_text": mainline[2]},
        "divergent": {
            "text": divergent[0],
            "branch_text": divergent[1],
            "converge_text": divergent[2],
            "flag": divergent[3],
            "suffix": divergent[4],
        },
    }


def generic_daily_choice_pair(anchor: str, scene_id: str) -> dict:
    variants = [
        {
            "choice_mode": "parallel",
            "mainline": ("先把话说完", "你把没说完的话补完整。", "对方听完以后，事情继续往下推进。"),
            "divergent": ("换个轻松说法", "你把语气放轻，换了个更容易接受的说法。", "气氛缓了一点，话题还是回到刚才那件事。", "flag_softened_tone", "soft_tone"),
        },
        {
            "choice_mode": "opposed",
            "mainline": ("留下来", "你停在原处，没有转身离开。", "短暂的停顿后，眼前的人继续说了下去。"),
            "divergent": ("先回去", "你退后半步，先把这件事放到一边。", "没走出多远，你还是被这件事拉了回来。", "flag_stepped_back", "step_back"),
        },
        {
            "choice_mode": "parallel",
            "mainline": ("先看桌上东西", "你低头看向桌面，把离手最近的东西拿起来。", "看过之后，你们又回到刚才的话题。"),
            "divergent": ("先看她的反应", "你没有碰桌上的东西，只看着她的表情。", "她很快避开视线，事情还是绕回桌边。", "flag_watched_reaction", "reaction"),
        },
        {
            "choice_mode": "opposed",
            "mainline": ("过去搭把手", "你走过去接过一半重量，让她先腾出手。", "事情做完以后，她才有空继续说话。"),
            "divergent": ("让他自己处理", "你退开半步，没有立刻插手。", "他忙完手里的事，还是把话接了下去。", "flag_let_handle_alone", "handle_alone"),
        },
        {
            "choice_mode": "parallel",
            "mainline": ("先点上灯", "你把灯点亮，屋里的影子往墙角退去。", "看清周围以后，你们继续处理眼前的事。"),
            "divergent": ("先把门带上", "你回身把门轻轻带上，外面的声音低了下去。", "屋里安静下来，话也更容易说出口。", "flag_closed_door", "close_door"),
        },
    ]
    variant = variants[_stable_index(scene_id, len(variants))]
    choice_mode = variant["choice_mode"]
    mainline = variant["mainline"]
    divergent = variant["divergent"]
    return {
        "choice_mode": choice_mode,
        "mainline": {"text": mainline[0], "branch_text": mainline[1], "converge_text": mainline[2]},
        "divergent": {
            "text": divergent[0],
            "branch_text": divergent[1],
            "converge_text": divergent[2],
            "flag": divergent[3],
            "suffix": divergent[4],
        },
    }


def scene_focus(anchor: str) -> str:
    if "纸条" in anchor or "纸" in anchor or "藏" in anchor:
        return "那张被藏起来的纸"
    if "门" in anchor or "脚步" in anchor:
        return "门边的动静"
    if "桌" in anchor or "茶杯" in anchor or "杯" in anchor:
        return "桌上的东西"
    if "椅" in anchor:
        return "椅子旁的人"
    if "饭" in anchor or "吃" in anchor:
        return "这顿饭"
    if "问" in anchor or "说" in anchor:
        return "刚才那句话"
    return "刚才那件事"


def _action_score(sentence: str) -> int:
    action_terms = ["问", "说", "走", "推", "停", "看", "拿", "藏", "递", "打开", "关上", "跟", "回", "坐", "吃"]
    return sum(1 for term in action_terms if term in sentence)


def _question_anchor(text: str) -> str:
    quoted_questions = re.findall(r"[“\"]([^”\"]*[？?][^”\"]*)[”\"]", text)
    if quoted_questions:
        return quoted_questions[0].strip(" ，,。！？!?；;")[:42]
    questions = [part.strip(" ，,。！？!?；;") for part in re.split(r"[。！？!?；;\n]", text) if "？" in part or "?" in part]
    if questions:
        return questions[0][:42]
    if "问" in text:
        sentences = [part.strip(" ，,。！？!?；;") for part in re.split(r"[。！？!?；;\n]", text) if "问" in part]
        if sentences:
            return sentences[0][:42]
    return ""


def _has_question(text: str) -> bool:
    question_terms = ["？", "?", "为什么", "怎么", "什么", "谁", "哪", "要不要", "能不能", "可不可以", "行不行", "问"]
    return any(term in text for term in question_terms)


def _normalize_choice_texts(choice: dict, add_aside: bool = False) -> dict:
    normalized = dict(choice)
    normalized["branch_text"] = _as_player_text(str(normalized.get("branch_text", "")), add_aside=add_aside)
    normalized["converge_text"] = _as_player_text(str(normalized.get("converge_text", "")), add_aside=False)
    return normalized


def _as_player_text(text: str, add_aside: bool) -> str:
    cleaned = text.replace("你们", "我们").replace("你", "我")
    if add_aside:
        return _with_action_aside(cleaned)
    return cleaned


def _with_action_aside(text: str) -> str:
    if "（" in text:
        return text
    asides = [
        "（心里斟酌了一下）",
        "（动作放轻了些）",
        "（还是决定试一试）",
        "（不想再拖下去）",
    ]
    aside = asides[_stable_index(text, len(asides))]
    if text.startswith("我"):
        return f"我{aside}{text[1:]}"
    return f"{aside}{text}"


def _stable_index(seed: str, size: int) -> int:
    return sum(ord(char) for char in seed) % size
