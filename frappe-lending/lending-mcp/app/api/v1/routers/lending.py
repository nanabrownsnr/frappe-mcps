from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from logging import getLogger

from fastapi import APIRouter, Depends, HTTPException, Query

from core.platfom_integration_client import PlatformIntegrationClient, get_platform_client
from schemas.lending import (
    CustomerCreateRequest,
    CustomerListResponse,
    DashboardOverviewResponse,
    CustomerUpdateRequest,
    DemoSeedRequest,
    DueDetailsResponse,
    LoanDashboardSummaryResponse,
    LoanCreateRequest,
    LoanListRequest,
    LoanOutstandingReportRequest,
    LoanUpdateMetadataRequest,
    RepaymentScheduleQuoteRequest,
)
from services.frappe_client import FrappeApiClient

logger = getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["mcp-tools"])

ACTIVE_LOAN_STATUSES = ["Disbursed", "Partially Disbursed", "Active"]


async def get_frappe_client(
    platform_client: PlatformIntegrationClient = Depends(get_platform_client),
) -> FrappeApiClient:
    return await FrappeApiClient.from_platform_client(platform_client)


@router.post("/customers", operation_id="customer_create", summary="Create customer")
async def create_customer(
    payload: CustomerCreateRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.call_method(
            "lending.mcp_api.create_customer",
            params=payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.exception("Customer create failed")
        raise HTTPException(status_code=400, detail=f"Unable to create customer: {exc}") from exc


@router.get("/customers/{customer_name}", operation_id="customer_get", summary="Get customer")
async def get_customer(
    customer_name: str,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.get_doc("Customer", customer_name)
    except Exception as exc:
        logger.exception("Customer get failed")
        raise HTTPException(status_code=404, detail=f"Unable to fetch customer: {exc}") from exc


@router.patch("/customers/{customer_name}", operation_id="customer_update", summary="Update customer")
async def update_customer(
    customer_name: str,
    payload: CustomerUpdateRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.update_doc(
            "Customer",
            customer_name,
            payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.exception("Customer update failed")
        raise HTTPException(status_code=400, detail=f"Unable to update customer: {exc}") from exc


@router.get("/customers", operation_id="customer_list", summary="List customers", response_model=CustomerListResponse)
async def list_customers(
    limit_page_length: int = Query(default=20, ge=1, le=200),
    order_by: str = Query(default="modified desc"),
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        data = await frappe_client.list_docs(
            "Customer",
            fields=["name", "customer_name", "customer_group", "territory", "mobile_no", "email_id"],
            limit_page_length=limit_page_length,
            order_by=order_by,
        )
        return {"data": data}
    except Exception as exc:
        logger.exception("Customer list failed")
        raise HTTPException(status_code=400, detail=f"Unable to list customers: {exc}") from exc


@router.get("/companies", operation_id="company_list", summary="List companies")
async def list_companies(
    limit_page_length: int = Query(default=50, ge=1, le=200),
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.call_method(
            "lending.mcp_api.list_companies",
            params={"limit_page_length": limit_page_length},
        )
    except Exception as exc:
        logger.exception("Company list failed")
        raise HTTPException(status_code=400, detail=f"Unable to list companies: {exc}") from exc


@router.get("/loan-products", operation_id="loan_product_list", summary="List loan products")
async def list_loan_products(
    company: str | None = None,
    limit_page_length: int = Query(default=50, ge=1, le=200),
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.call_method(
            "lending.mcp_api.list_loan_products",
            params={
                "company": company,
                "limit_page_length": limit_page_length,
            },
        )
    except Exception as exc:
        logger.exception("Loan product list failed")
        raise HTTPException(status_code=400, detail=f"Unable to list loan products: {exc}") from exc


@router.get("/loans/{loan_name}", operation_id="loan_get", summary="Get loan")
async def get_loan(
    loan_name: str,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.get_doc("Loan", loan_name)
    except Exception as exc:
        logger.exception("Loan get failed")
        raise HTTPException(status_code=404, detail=f"Unable to fetch loan: {exc}") from exc


@router.post("/loans", operation_id="loan_create", summary="Create draft loan")
async def create_loan(
    payload: LoanCreateRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.call_method(
            "lending.mcp_api.create_loan",
            params=payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.exception("Loan create failed")
        raise HTTPException(status_code=400, detail=f"Unable to create loan: {exc}") from exc


@router.get("/loans", operation_id="loan_list", summary="List loans")
async def list_loans(
    company: str | None = None,
    applicant: str | None = None,
    status: list[str] | None = Query(default=None),
    limit_page_length: int = Query(default=20, ge=1, le=200),
    order_by: str = Query(default="modified desc"),
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        filters: list[list] = []
        if company:
            filters.append(["Loan", "company", "=", company])
        if applicant:
            filters.append(["Loan", "applicant", "=", applicant])
        if status:
            filters.append(["Loan", "status", "in", status])

        return await frappe_client.list_docs(
            "Loan",
            fields=[
                "name",
                "applicant",
                "company",
                "loan_product",
                "status",
                "loan_amount",
                "disbursed_amount",
                "days_past_due",
                "is_npa",
                "posting_date",
            ],
            filters=filters or None,
            limit_page_length=limit_page_length,
            order_by=order_by,
        )
    except Exception as exc:
        logger.exception("Loan list failed")
        raise HTTPException(status_code=400, detail=f"Unable to list loans: {exc}") from exc


@router.patch("/loans/{loan_name}/metadata", operation_id="loan_update_metadata", summary="Update safe loan metadata")
async def update_loan_metadata(
    loan_name: str,
    payload: LoanUpdateMetadataRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.update_doc(
            "Loan",
            loan_name,
            payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.exception("Loan update failed")
        raise HTTPException(status_code=400, detail=f"Unable to update loan metadata: {exc}") from exc


@router.post("/loans/repayment-schedule/quote", operation_id="loan_quote_repayment_schedule", summary="Quote repayment schedule")
async def quote_repayment_schedule(
    payload: RepaymentScheduleQuoteRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.call_method("lending.api.get_repayment_schedule", params=payload.model_dump())
    except Exception as exc:
        logger.exception("Repayment schedule quote failed")
        raise HTTPException(status_code=400, detail=f"Unable to quote repayment schedule: {exc}") from exc


@router.get("/loans/{loan_name}/due-details", operation_id="loan_get_due_details", summary="Get loan due details", response_model=DueDetailsResponse)
async def get_due_details(
    loan_name: str,
    as_on_date: str,
    loan_disbursement: str | None = None,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        data = await frappe_client.call_method(
            "lending.api.get_due_details",
            params={
                "loan": loan_name,
                "as_on_date": as_on_date,
                "loan_disbursement": loan_disbursement,
            },
        )
        return {"data": data}
    except Exception as exc:
        logger.exception("Due details failed")
        raise HTTPException(status_code=400, detail=f"Unable to fetch due details: {exc}") from exc


@router.get("/loans/{loan_name}/dashboard-summary", operation_id="loan_dashboard_summary", summary="Get dashboard-style loan summary")
async def loan_dashboard_summary(
    loan_name: str,
    as_on_date: str,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        loan_doc, due_details = await asyncio.gather(
            frappe_client.get_doc("Loan", loan_name),
            frappe_client.call_method(
                "lending.api.get_due_details",
                params={"loan": loan_name, "as_on_date": as_on_date},
            ),
        )
        return {
            "loan": {
                "name": loan_doc.get("name"),
                "applicant": loan_doc.get("applicant"),
                "company": loan_doc.get("company"),
                "loan_product": loan_doc.get("loan_product"),
                "status": loan_doc.get("status"),
                "loan_amount": loan_doc.get("loan_amount"),
                "disbursed_amount": loan_doc.get("disbursed_amount"),
                "days_past_due": loan_doc.get("days_past_due"),
                "is_npa": loan_doc.get("is_npa"),
                "classification_code": loan_doc.get("classification_code"),
                "classification_name": loan_doc.get("classification_name"),
                "total_principal_paid": loan_doc.get("total_principal_paid"),
                "total_interest_payable": loan_doc.get("total_interest_payable"),
                "written_off_amount": loan_doc.get("written_off_amount"),
            },
            "summary": due_details,
        }
    except Exception as exc:
        logger.exception("Loan dashboard summary failed")
        raise HTTPException(status_code=400, detail=f"Unable to build loan dashboard summary: {exc}") from exc


@router.get(
    "/dashboard/overview",
    operation_id="dashboard_overview",
    summary="Get lending overview",
    response_model=DashboardOverviewResponse,
)
async def dashboard_overview(
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        overview = await frappe_client.call_method("lending.mcp_api.get_dashboard_overview")
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "cards": overview.get("cards", {}),
        }
    except Exception as exc:
        logger.exception("Dashboard overview failed")
        raise HTTPException(status_code=400, detail=f"Unable to fetch dashboard overview: {exc}") from exc


@router.get(
    "/dashboard/loan-summary",
    operation_id="dashboard_loan_summary",
    summary="Get dashboard-oriented loan portfolio summary",
    response_model=LoanDashboardSummaryResponse,
)
async def dashboard_loan_summary(
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        overview_task = frappe_client.call_method("lending.mcp_api.get_dashboard_overview")
        portfolio_loans_task = frappe_client.list_docs(
            "Loan",
            fields=[
                "name",
                "applicant",
                "loan_product",
                "status",
                "loan_amount",
                "disbursed_amount",
                "total_principal_paid",
                "days_past_due",
                "posting_date",
            ],
            filters=[["Loan", "status", "in", ACTIVE_LOAN_STATUSES]],
            limit_page_length=100,
            order_by="posting_date desc",
        )

        overview, portfolio_loans = await asyncio.gather(
            overview_task,
            portfolio_loans_task,
        )

        generated_at = datetime.now(UTC).isoformat()
        cards = overview.get("cards", {})
        outstanding_rows = []
        for row in portfolio_loans:
            principal_base = float(row.get("disbursed_amount") or row.get("loan_amount") or 0)
            principal_paid = float(row.get("total_principal_paid") or 0)
            outstanding_rows.append(
                {
                    **row,
                    "pending_principal_amount": max(principal_base - principal_paid, 0),
                }
            )
        top_outstanding = sorted(
            outstanding_rows,
            key=lambda row: float(row.get("pending_principal_amount") or 0),
            reverse=True,
        )[:5]
        outstanding_totals = {
            "pending_principal_amount": sum(float(row.get("pending_principal_amount") or 0) for row in outstanding_rows),
            "total_amount_paid": sum(float(row.get("total_principal_paid") or 0) for row in outstanding_rows),
            "loan_count": len(outstanding_rows),
        }

        return {
            "generated_at": generated_at,
            "overview": {
                "generated_at": generated_at,
                "cards": cards,
            },
            "hero_cards": [
                {
                    "key": "active_loans",
                    "label": "Active Loans",
                    "value": str(cards.get("active_loans", 0)),
                    "tone": "accent",
                },
                {
                    "key": "open_loan_applications",
                    "label": "Open Applications",
                    "value": str(cards.get("open_loan_applications", 0)),
                    "tone": "default",
                },
                {
                    "key": "closed_loans",
                    "label": "Closed Loans",
                    "value": str(cards.get("closed_loans", 0)),
                    "tone": "default",
                },
                {
                    "key": "total_disbursed",
                    "label": "Total Disbursed",
                    "value": f"{float(cards.get('total_disbursed', 0)):,.2f}",
                    "tone": "success",
                },
                {
                    "key": "total_repayment",
                    "label": "Total Repayment",
                    "value": f"{float(cards.get('total_repayment', 0)):,.2f}",
                    "tone": "warning",
                },
            ],
            "recent_loans": portfolio_loans[:5],
            "top_outstanding": top_outstanding,
            "outstanding_totals": outstanding_totals,
            "actions": [
                {
                    "label": "Portfolio Overview",
                    "tool": "dashboard_overview",
                    "description": "Fetch the canonical portfolio snapshot used by the dashboard.",
                },
                {
                    "label": "Outstanding Report",
                    "tool": "report_loan_outstanding",
                    "description": "Inspect principal outstanding, paid amounts, overdue values, and status by loan.",
                },
                {
                    "label": "Loan List",
                    "tool": "loan_list",
                    "description": "Drill into the active loan set and inspect individual records.",
                },
            ],
        }
    except Exception as exc:
        logger.exception("Dashboard loan summary failed")
        raise HTTPException(status_code=400, detail=f"Unable to fetch dashboard loan summary: {exc}") from exc


@router.post("/demo/seed-basic", operation_id="demo_seed_basic", summary="Seed a basic lending demo")
async def seed_basic_demo(
    payload: DemoSeedRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        companies = await frappe_client.call_method(
            "lending.mcp_api.list_companies",
            params={"limit_page_length": 100},
        )
        selected_company = payload.company or (companies[0]["name"] if companies else None)
        if not selected_company:
            return {
                "customer": None,
                "company": None,
                "loan_product": None,
                "loan": None,
                "warnings": [
                    "No Company records found. Complete ERPNext company setup before seeding demo lending data."
                ],
            }

        customer_rows = await frappe_client.list_docs(
            "Customer",
            fields=["name", "customer_name"],
            filters=[["Customer", "customer_name", "=", payload.customer_name]],
            limit_page_length=1,
        )
        if customer_rows:
            customer = await frappe_client.get_doc("Customer", customer_rows[0]["name"])
        else:
            customer = await frappe_client.call_method(
                "lending.mcp_api.create_customer",
                params={
                    "customer_name": payload.customer_name,
                    "customer_type": "Individual",
                    "customer_group": payload.customer_group,
                    "territory": payload.territory,
                    "mobile_no": payload.mobile_no,
                    "email_id": payload.email_id,
                },
            )

        loan_products = await frappe_client.call_method(
            "lending.mcp_api.list_loan_products",
            params={
                "company": selected_company,
                "limit_page_length": 100,
            },
        )
        selected_loan_product = payload.loan_product or (loan_products[0]["name"] if loan_products else None)

        loan = None
        if selected_company and selected_loan_product:
            existing_loans = await frappe_client.list_docs(
                "Loan",
                fields=["name", "applicant", "company", "loan_product", "status"],
                filters=[
                    ["Loan", "applicant", "=", customer["name"]],
                    ["Loan", "company", "=", selected_company],
                    ["Loan", "loan_product", "=", selected_loan_product],
                ],
                limit_page_length=1,
                order_by="modified desc",
            )
            if existing_loans:
                loan = await frappe_client.get_doc("Loan", existing_loans[0]["name"])
            else:
                loan_payload: dict[str, object] = {
                    "applicant_type": "Customer",
                    "applicant": customer["name"],
                    "company": selected_company,
                    "loan_product": selected_loan_product,
                    "loan_amount": payload.loan_amount,
                }
                if payload.posting_date:
                    loan_payload["posting_date"] = payload.posting_date
                effective_rate = payload.rate_of_interest or (
                    loan_products[0].get("rate_of_interest") if loan_products else None
                )
                if effective_rate is not None:
                    loan_payload["rate_of_interest"] = effective_rate
                if payload.repayment_method:
                    loan_payload["repayment_method"] = payload.repayment_method
                if payload.repayment_periods is not None:
                    loan_payload["repayment_periods"] = payload.repayment_periods
                if payload.repayment_start_date:
                    loan_payload["repayment_start_date"] = payload.repayment_start_date
                loan = await frappe_client.call_method("lending.mcp_api.create_loan", params=loan_payload)

        return {
            "customer": customer,
            "company": selected_company,
            "loan_product": selected_loan_product,
            "loan": loan,
            "warnings": [
                message
                for message in [
                    None if selected_company else "No Company records found; loan seed skipped.",
                    None if selected_loan_product else "No Loan Product records found; loan seed skipped.",
                ]
                if message
            ],
        }
    except Exception as exc:
        logger.exception("Basic demo seed failed")
        raise HTTPException(status_code=400, detail=f"Unable to seed basic demo: {exc}") from exc


@router.post("/reports/loan-outstanding", operation_id="report_loan_outstanding", summary="Run loan outstanding report")
async def report_loan_outstanding(
    payload: LoanOutstandingReportRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        return await frappe_client.run_report(
            "Loan Outstanding Report",
            filters=payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.exception("Loan outstanding report failed")
        raise HTTPException(status_code=400, detail=f"Unable to run loan outstanding report: {exc}") from exc
