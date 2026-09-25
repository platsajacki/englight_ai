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


def make_got_it_button(word_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Got it', callback_data=f'sure_gotit_{word_id}')]]
    )


def make_cancel_check_button(word_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text='Cancel', callback_data=f'cancel_check_{word_id}')]]
    )


def make_delete_buttons(words: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=part_of_speech, callback_data=f'delete_{word_id}')]
            for word_id, part_of_speech in words
        ]
    )
