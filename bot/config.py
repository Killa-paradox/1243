from dataclasses import dataclass
import os
from dotenv import load_dotenv


load_dotenv()


@dataclass(slots=True)
class Config:
    bot_token: str
    db_path: str = "bot.db"


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Add it to .env")

    return Config(
        bot_token=token,
        db_path=os.getenv("DB_PATH", "bot.db"),
    )
