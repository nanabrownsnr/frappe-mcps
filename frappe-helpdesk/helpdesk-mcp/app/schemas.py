from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    subject: str
    description: str | None = None
    raised_by: str | None = Field(default=None, description="Customer email address")
    priority: str | None = None
    status: str | None = None
    ticket_type: str | None = None
    agent_group: str | None = None
    customer: str | None = None
    contact: str | None = None


class TicketUpdate(BaseModel):
    subject: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    ticket_type: str | None = None
    agent_group: str | None = None
    customer: str | None = None
    contact: str | None = None
    resolution_details: str | None = None


class TicketReply(BaseModel):
    content: str
    commented_by: str | None = None
    is_pinned: bool = False


class TicketAssign(BaseModel):
    assign_to: str = Field(description="User email or agent user id")
    description: str | None = "Assigned from Helpdesk MCP"


class CustomerCreate(BaseModel):
    customer_name: str
    domain: str | None = None


class CustomerUpdate(BaseModel):
    customer_name: str | None = None
    domain: str | None = None


class ListResponse(BaseModel):
    data: list[dict[str, Any]]


class SuccessResponse(BaseModel):
    data: dict[str, Any]
