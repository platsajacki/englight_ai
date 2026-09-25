from aiogram.fsm.state import State, StatesGroup


class PromptStates(StatesGroup):
    waiting_for_prompt = State()


class ReviewStates(StatesGroup):
    waiting_for_sentence = State()
