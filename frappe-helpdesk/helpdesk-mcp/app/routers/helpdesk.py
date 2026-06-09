from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from schemas import (
    CustomerCreate,
    CustomerUpdate,
    ListResponse,
    SuccessResponse,
    TicketAssign,
    TicketCreate,
    TicketReply,
    TicketUpdate,
)
from services.frappe_client import FrappeApiClient, get_frappe_client

router = APIRouter(prefix="/api/v1", tags=["mcp-tools"])


def clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def to_http_error(exc: Exception, default_status: int, default_prefix: str) -> HTTPException:
    if isinstance(exc, HTTPException):
        return exc
    return HTTPException(status_code=default_status, detail=f"{default_prefix}: {exc}")


@router.post("/tickets", operation_id="ticket_create", summary="Create support ticket", response_model=SuccessResponse)
async def ticket_create(payload: TicketCreate, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        ticket = await frappe.create_doc("HD Ticket", clean_payload(payload.model_dump()))
        return {"data": ticket}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to create ticket") from exc


@router.get("/tickets/{ticket_name}", operation_id="ticket_get", summary="Get support ticket", response_model=SuccessResponse)
async def ticket_get(ticket_name: str, include_comments: bool = True, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        ticket = await frappe.get_doc("HD Ticket", ticket_name)
        if include_comments:
            ticket["comments"] = await frappe.list_docs(
                "HD Ticket Comment",
                fields=["name", "commented_by", "content", "is_pinned", "creation"],
                filters={"reference_ticket": ticket_name},
                order_by="creation asc",
                limit_page_length=100,
        )
        return {"data": ticket}
    except Exception as exc:
        raise to_http_error(exc, 404, "Unable to get ticket") from exc


@router.get("/tickets", operation_id="ticket_list", summary="List support tickets", response_model=ListResponse)
async def ticket_list(
    status: str | None = None,
    priority: str | None = None,
    customer: str | None = None,
    raised_by: str | None = None,
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    frappe: FrappeApiClient = Depends(get_frappe_client),
):
    filters: list[list[Any]] = []
    for field, value in {
        "status": status,
        "priority": priority,
        "customer": customer,
        "raised_by": raised_by,
    }.items():
        if value:
            filters.append(["HD Ticket", field, "=", value])
    if query:
        filters.append(["HD Ticket", "subject", "like", f"%{query}%"])

    rows = await frappe.list_docs(
        "HD Ticket",
        fields=[
            "name",
            "subject",
            "raised_by",
            "status",
            "priority",
            "customer",
            "agent_group",
            "modified",
            "creation",
        ],
        filters=filters or None,
        order_by="modified desc",
        limit_page_length=limit,
    )
    return {"data": rows}


@router.patch("/tickets/{ticket_name}", operation_id="ticket_update", summary="Update support ticket", response_model=SuccessResponse)
async def ticket_update(ticket_name: str, payload: TicketUpdate, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        ticket = await frappe.update_doc("HD Ticket", ticket_name, clean_payload(payload.model_dump()))
        return {"data": ticket}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to update ticket") from exc


@router.post("/tickets/{ticket_name}/reply", operation_id="ticket_reply", summary="Add reply/comment to ticket", response_model=SuccessResponse)
async def ticket_reply(ticket_name: str, payload: TicketReply, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        comment = await frappe.create_doc(
            "HD Ticket Comment",
            clean_payload(
                {
                    "reference_ticket": ticket_name,
                    "content": payload.content,
                    "commented_by": payload.commented_by,
                    "is_pinned": int(payload.is_pinned),
                }
            ),
        )
        return {"data": comment}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to add ticket reply") from exc


@router.post("/tickets/{ticket_name}/assign", operation_id="ticket_assign", summary="Assign support ticket", response_model=SuccessResponse)
async def ticket_assign(ticket_name: str, payload: TicketAssign, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        result = await frappe.call_method(
            "frappe.desk.form.assign_to.add",
            {
                "doctype": "HD Ticket",
                "name": ticket_name,
                "assign_to": [payload.assign_to],
                "description": payload.description,
            },
        )
        return {"data": {"ticket": ticket_name, "assignment": result}}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to assign ticket") from exc


@router.post("/customers", operation_id="customer_create", summary="Create helpdesk customer", response_model=SuccessResponse)
async def customer_create(payload: CustomerCreate, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        customer = await frappe.create_doc("HD Customer", clean_payload(payload.model_dump()))
        return {"data": customer}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to create customer") from exc


@router.get("/customers/{customer_name}", operation_id="customer_get", summary="Get helpdesk customer", response_model=SuccessResponse)
async def customer_get(customer_name: str, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        customer = await frappe.get_doc("HD Customer", customer_name)
        return {"data": customer}
    except Exception as exc:
        raise to_http_error(exc, 404, "Unable to get customer") from exc


@router.patch("/customers/{customer_name}", operation_id="customer_update", summary="Update helpdesk customer", response_model=SuccessResponse)
async def customer_update(customer_name: str, payload: CustomerUpdate, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        customer = await frappe.update_doc("HD Customer", customer_name, clean_payload(payload.model_dump()))
        return {"data": customer}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to update customer") from exc


@router.get("/customers", operation_id="customer_list", summary="List helpdesk customers", response_model=ListResponse)
async def customer_list(
    query: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    frappe: FrappeApiClient = Depends(get_frappe_client),
):
    filters = [["HD Customer", "customer_name", "like", f"%{query}%"]] if query else None
    rows = await frappe.list_docs(
        "HD Customer",
        fields=["name", "customer_name", "domain", "modified"],
        filters=filters,
        order_by="modified desc",
        limit_page_length=limit,
    )
    return {"data": rows}


@router.get("/agents", operation_id="agent_list", summary="List helpdesk agents", response_model=ListResponse)
async def agent_list(active_only: bool = True, frappe: FrappeApiClient = Depends(get_frappe_client)):
    filters = {"is_active": 1} if active_only else None
    rows = await frappe.list_docs(
        "HD Agent",
        fields=["name", "user", "agent_name", "user_image", "is_active", "modified"],
        filters=filters,
        order_by="modified desc",
        limit_page_length=100,
    )
    return {"data": rows}


@router.get("/articles/search", operation_id="knowledge_article_search", summary="Search helpdesk knowledge articles")
async def knowledge_article_search(query: str, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        results = await frappe.call_method("helpdesk.api.article.search", {"query": query})
        return {"data": results}
    except Exception as exc:
        raise to_http_error(exc, 400, "Unable to search articles") from exc


@router.get("/articles/{article_name}", operation_id="knowledge_article_get", summary="Get helpdesk knowledge article", response_model=SuccessResponse)
async def knowledge_article_get(article_name: str, frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        article = await frappe.get_doc("HD Article", article_name)
        return {"data": article}
    except Exception as exc:
        raise to_http_error(exc, 404, "Unable to get article") from exc


@router.get("/dashboard/summary", operation_id="dashboard_summary", summary="Get helpdesk dashboard summary")
async def dashboard_summary(frappe: FrappeApiClient = Depends(get_frappe_client)):
    try:
        status_rows = await frappe.list_docs(
            "HD Ticket Status",
            fields=["name", "category"],
            filters={"enabled": 1},
            limit_page_length=100,
        )
    except Exception:
        status_rows = await frappe.list_docs("HD Ticket Status", fields=["name", "category"], limit_page_length=100)

    try:
        total_tickets = await frappe.count("HD Ticket")
        unassigned = await frappe.count("HD Ticket", filters=[["HD Ticket", "_assign", "in", ["", "[]"]]])
    except Exception:
        total_tickets = 0
        unassigned = 0

    counts_by_status = {}
    counts_by_category = {}
    for row in status_rows:
        status = row.get("name")
        category = row.get("category") or "Uncategorized"
        if not status:
            continue
        count = await frappe.count("HD Ticket", filters={"status": status})
        counts_by_status[status] = count
        counts_by_category[category] = counts_by_category.get(category, 0) + count

    recent = await frappe.list_docs(
        "HD Ticket",
        fields=["name", "subject", "raised_by", "status", "priority", "modified"],
        order_by="modified desc",
        limit_page_length=10,
    )

    return {
        "total_tickets": total_tickets,
        "unassigned_tickets": unassigned,
        "counts_by_status": counts_by_status,
        "counts_by_category": counts_by_category,
        "recent_tickets": recent,
        "suggested_tools": [
            "ticket_list",
            "ticket_get",
            "ticket_update",
            "ticket_assign",
            "knowledge_article_search",
        ],
    }
