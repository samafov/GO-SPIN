from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import WEBAPP_URL

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎁 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))]
        ]
    )
    await message.answer(
        f"Добро пожаловать, {message.from_user.first_name}!\n\n"
        "🎄 Покупай коллекционные подарки за фиксированную цену в Stars\n"
        "🎡 Крути бесплатное колесо раз в 24 часа и собирай коллекцию\n\n"
        "Никаких ставок реальными деньгами — только фиксированные цены и бесплатные спины.",
        reply_markup=keyboard,
    )
