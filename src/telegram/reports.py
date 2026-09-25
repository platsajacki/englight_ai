from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from constants import REPETITION_INTERVALS, UTC
from database.models import WordProgress


@dataclass
class StatsReport:
    progresses: Sequence[WordProgress]

    @property
    def learned(self) -> int:
        return sum(wp.is_learned for wp in self.progresses)

    @property
    def due(self) -> int:
        now = datetime.now(tz=UTC)
        return sum(not wp.is_learned and wp.next_review <= now for wp in self.progresses)

    def levels(self) -> str:
        counter = Counter(wp.repetitions for wp in self.progresses if not wp.is_learned)
        return '\n'.join(f'  Level {level}: {counter[level]}' for level in REPETITION_INTERVALS)

    def render(self) -> str:
        return (
            f'<b>Total words:</b> {len(self.progresses)}\n'
            f'<b>Learned:</b> {self.learned}\n'
            f'<b>Due for review:</b> {self.due}\n'
            f'<b>By level:</b>\n{self.levels()}'
        )
