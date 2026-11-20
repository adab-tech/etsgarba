from collections import OrderedDict, deque


class ConversationStore:
    """In-memory per-user history. Swap for Redis/DB before scaling past one process."""

    def __init__(self, turns: int = 10, max_users: int = 10_000):
        self.turns = turns
        self.max_users = max_users
        self._data: OrderedDict[str, deque] = OrderedDict()

    def get(self, user: str) -> list[dict]:
        msgs = list(self._data.get(user, ()))
        # Anthropic requires the first message to be from the user.
        while msgs and msgs[0]["role"] != "user":
            msgs.pop(0)
        return msgs

    def add(self, user: str, role: str, content: str) -> None:
        if user not in self._data:
            if len(self._data) >= self.max_users:
                self._data.popitem(last=False)
            self._data[user] = deque(maxlen=self.turns * 2)
        self._data.move_to_end(user)
        self._data[user].append({"role": role, "content": content})

    def pop_last(self, user: str) -> None:
        if self._data.get(user):
            self._data[user].pop()

    def clear(self, user: str) -> None:
        self._data.pop(user, None)
