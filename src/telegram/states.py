from aiogram.fsm.state import State, StatesGroup


class PromptStates(StatesGroup):
    waiting_for_translate_prompt = State()
