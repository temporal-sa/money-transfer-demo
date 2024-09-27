from dataclasses import dataclass

from app.models import SCENARIOS, ACCOUNT_TYPES, ELIGIBLE_RECIPIENTS


async def get_transfer_money_form() -> dict:
    return {
        'scenarios': SCENARIOS,
        'account_types': ACCOUNT_TYPES,
        'eligible_recipients': ELIGIBLE_RECIPIENTS
    }

@dataclass
class ServerSentEvent:
    data: str
    retry: int | None
    event: str | None = None
    id: int | None = None

    def encode(self) -> bytes:
        message = f"data: {self.data}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\n\n"
        return message.encode('utf-8')