from __future__ import annotations

from .config import settings
from .database import conversation_count, latest_memory_summary, recent_conversation, save_memory_summary


def memory_context() -> dict:
    return {
        "summary": latest_memory_summary(),
        "recent_messages": recent_conversation(settings.memory_recent_messages),
        "message_count": conversation_count(),
    }


def maybe_compact_memory() -> str:
    count = conversation_count()
    if count < settings.memory_compaction_threshold:
        return latest_memory_summary()

    messages = recent_conversation(min(count, 30))
    user_topics = [item["content"][:180] for item in messages if item["role"] == "user"]
    assistant_outcomes = [item["content"][:220] for item in messages if item["role"] == "assistant"]
    summary = (
        "Recent user objectives: " + " | ".join(user_topics[-8:]) + "\n"
        "Recent assistant findings: " + " | ".join(assistant_outcomes[-6:])
    )[:5000]
    previous = latest_memory_summary()
    if previous:
        summary = (previous[-2500:] + "\n" + summary)[-5000:]
    save_memory_summary(summary, count)
    return summary
