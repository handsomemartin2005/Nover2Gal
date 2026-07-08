from __future__ import annotations

from app.schemas.story import Clue, POVKnowledgeState, StoryEvent


def build_pov_knowledge(
    project_id: str,
    pov_character: str,
    events: list[StoryEvent],
    clues: list[Clue],
) -> list[POVKnowledgeState]:
    states: list[POVKnowledgeState] = []
    known: list[str] = []
    unknown: list[str] = []
    suspected: list[str] = []
    forbidden: list[str] = []

    clue_by_event = {clue.first_appears_event_id: clue for clue in clues}

    for event in sorted(events, key=lambda item: item.order):
        if pov_character in event.visible_to:
            _append_unique(known, event.text)
            if event.hidden_meaning:
                _append_unique(suspected, _surface_suspicion(event))
                _append_unique(forbidden, event.hidden_meaning)
        else:
            _append_unique(unknown, event.text)
            if event.hidden_meaning:
                _append_unique(forbidden, event.hidden_meaning)

        clue = clue_by_event.get(event.event_id)
        if clue and clue.reveal_policy.startswith("do_not_reveal"):
            _append_unique(forbidden, clue.hidden_meaning)

        states.append(
            POVKnowledgeState(
                project_id=project_id,
                after_event_order=event.order,
                known_facts=list(known),
                unknown_facts=list(unknown),
                suspected_facts=list(suspected),
                false_beliefs=[],
                forbidden_reveals=list(forbidden),
            )
        )
    return states


def _surface_suspicion(event: StoryEvent) -> str:
    return f"{event.text} 可能隐藏了尚未确认的信息。"


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)
