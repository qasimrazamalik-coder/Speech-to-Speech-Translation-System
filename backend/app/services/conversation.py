from collections import defaultdict, deque


class ConversationMemory:
    def __init__(self, max_turns: int = 8) -> None:
        self.turns: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=max_turns))

    def add(self, user: str, source: str, translated: str) -> None:
        self.turns[user].append(f"source={source}; translated={translated}")

    def get(self, user: str) -> list[str]:
        return list(self.turns[user])
