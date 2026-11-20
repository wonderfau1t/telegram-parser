"""Вход в аккаунт Telegram по QR-коду с сохранением сессии в файл.

Запуск на VPS (без TTY, через журналы контейнера):

    docker compose run --rm --no-deps parser python -m src.qr_auth

QR-код выводится ASCII-графикой в stdout (виден в `docker compose logs`
или прямо в терминале), а также сохраняется как PNG в /data/qr.png
(внутри volume parser_data). Откройте Telegram на телефоне:
Настройки -> Устройства -> Подключить устройство -> сканируйте QR.

Ссылку tg://login?token=... можно открыть на компьютере с установленным
Telegram Desktop: он предложит подтвердить вход.

При включённой 2FA задайте пароль в переменной окружения TELEGRAM_2FA_PASSWORD
(например, через `TELEGRAM_2FA_PASSWORD=... docker compose run ...`).
"""

import asyncio
import io
import os
import sys

from telethon import TelegramClient, errors

from src.client import create_client
from src.config import get_settings

PNG_PATH = os.environ.get("QR_PNG_PATH", "/data/qr.png")


def render_ascii(url: str) -> str:
    """ASCII QR для журналов контейнера; требует пакет qrcode."""
    import qrcode

    buf = io.StringIO()
    qr = qrcode.QRCode(border=2)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(out=buf, invert=True)
    return buf.getvalue()


def render_png(url: str, path: str) -> None:
    """Сохранить QR картинкой (например, в volume /data)."""
    import qrcode

    img = qrcode.make(url)
    img.save(path)


async def authorize(client: TelegramClient) -> None:
    me = await client.get_me()
    print(f"Авторизация завершена: {me.first_name} (id={me.id}).")
    print("Сессия сохранена, можно запускать парсер: docker compose up -d parser")


async def handle_password(client: TelegramClient) -> None:
    password = os.environ.get("TELEGRAM_2FA_PASSWORD", "")
    if not password and sys.stdin.isatty():
        password = input("Введите пароль 2FA: ").strip()
    if not password:
        raise RuntimeError(
            "Включена двухфакторная аутентификация. Перезапустите с переменной "
            "TELEGRAM_2FA_PASSWORD=<пароль>."
        )
    await client.sign_in(password=password)


async def login_by_qr(client: TelegramClient) -> None:
    while not await client.is_user_authorized():
        qr = await client.qr_login()
        print(
            "Откройте Telegram на телефоне: Настройки -> Устройства -> "
            "Подключить устройство и наведите камеру на QR-код."
        )
        print(f"Ссылка для Telegram Desktop: {qr.url}")
        try:
            print(render_ascii(qr.url))
        except Exception:  # qrcode не установлен — ссылка выше остаётся рабочей
            print("(Пакет qrcode не установлен, ASCII-код не показан.)")
        try:
            render_png(qr.url, PNG_PATH)
            print(f"PNG сохранён: {PNG_PATH}")
        except Exception:
            pass

        try:
            # Ждём сканирования и подтверждения; True = успех.
            if not await qr.wait():
                continue
        except errors.SessionPasswordNeededError:
            await handle_password(client)
        except errors.QrTokenExpiredError:
            print("QR-код истёк, генерирую новый...")
            continue

        if not await client.is_user_authorized():
            continue

        await authorize(client)
        return

    await authorize(client)


async def main() -> None:
    client = create_client(get_settings())
    await client.connect()
    try:
        await login_by_qr(client)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
