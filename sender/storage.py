import json
from pathlib import Path


def load_chats(path: Path) -> set[int]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or any(type(chat_id) is not int for chat_id in data):
        raise ValueError(f"{path}: ожидается JSON-массив числовых ID чатов")
    return set(data)


def save_chats(path: Path, chats: set[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(sorted(chats), indent=2) + "\n", encoding="utf-8")
    # Replace only after writing the complete list to avoid a partially written JSON.
    temporary.replace(path)
