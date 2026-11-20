"""Диагностика отправки кода: покажет точную ошибку или подтверждение."""
import asyncio
import traceback

from telethon import errors

from src.client import create_client
from src.config import get_settings


async def main():
    phone = input("Телефон (+7…): ").strip()
    client = create_client(get_settings())
    await client.connect()
    try:
        print("Подключение:", client.is_connected())
        try:
            sent = await client.send_code_request(phone)
            print(f"OK: код отправлен. Тип доставки: {sent.type}. "
                  f"Проверьте приложение Telegram (чат Telegram / SMS).")
        except errors.FloodWaitError as e:
            print(f"FLOOD_WAIT: Telegram блокирует отправку кода. "
                  f"Подождите {e.seconds // 60} мин {e.seconds % 60} сек и повторите.")
        except errors.ApiIdInvalidError:
            print("API_ID/API_HASH неверны — выданы для другого аккаунта или скопированы с ошибкой.")
        except errors.PhoneNumberInvalidError:
            print("Номер телефона в неверном формате (нужно +7XXXXXXXXXX).")
        except errors.PhoneNumberBannedError:
            print("Этот номер забанен в Telegram.")
        except Exception:
            print("Неожиданная ошибка:")
            traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
