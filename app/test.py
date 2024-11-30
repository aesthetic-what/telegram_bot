from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import asyncio

keyboard_test = InlineKeyboardMarkup(
    inline_keyboard=[
        [   
            InlineKeyboardButton(text='pay', pay=True),
            InlineKeyboardButton(text="back", callback_data="back_to_menu"),
            InlineKeyboardButton(
                text="RickRoll", url="https://www.youtube.com/watch?v=-4s_wbKGBTg"
            ),
        ],
    ]
)


@router.message(Command("pidori"))
async def pidori(message: Message):
    await message.answer_invoice(
        "сосать хуй",
        "sosal?",
        "Саня хуй соси",
        "XTR",
        [LabeledPrice(label="XTR", amount=1)],
        reply_markup=keyboard_test,
    )


@router.pre_checkout_query()
async def sosal(query: PreCheckoutQuery):
    await query.answer(True)


@router.message(F.successful_payment)
async def real_sosal(message: Message):
    await message.answer(
        f"charge id: {message.successful_payment.telegram_payment_charge_id}"
    )


@router.message(Command("obratno_sosal"))
async def dablin(message: Message):
    args = message.text.split(" ")
    if len(args) == 1:
        await message.answer("Удерживай /obratno_sosal и напиши айди платежа")
    else:
        charge_id = args[1]
        await bot.refund_star_payment(message.chat.id, charge_id)