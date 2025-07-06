from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def make_know_or_not_buttons(word_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text='I know', callback_data=f'know_{word_id}'),
                InlineKeyboardButton(text='I don\'t know', callback_data=f'not_know_{word_id}'),
            ]
        ]
    )


def make_sure_buttons(word_id: int, is_know: bool) -> InlineKeyboardMarkup:
    inline_keyboard = (
        [
            [
                InlineKeyboardButton(text='Yes', callback_data=f'sure_yes_{word_id}'),
                InlineKeyboardButton(text='No', callback_data=f'sure_no_{word_id}'),
            ]
        ]
        if is_know
        else [
            [
                InlineKeyboardButton(text='Got it', callback_data=f'sure_gotit_{word_id}'),
            ]
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)
