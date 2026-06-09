from pydantic import BaseModel


class SubscriptionState(BaseModel):
    active: bool = True
    plan: str | None = None
