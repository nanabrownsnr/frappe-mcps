from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from json import JSONDecodeError, loads
from logging import getLogger

from fastapi import APIRouter, Depends, HTTPException, Query

from core.platfom_integration_client import PlatformIntegrationClient, get_platform_client
from schemas.lending import (
    CustomerCreateRequest,
    CustomerListResponse,
    CustomerUpdateRequest,
    DueDetailsResponse,
    LoanMutationResponse,
    LoanDashboardSummaryResponse,
    LoanCreateRequest,
    LoanListRequest,
    LoanOutstandingReportRequest,
    PrepareNewLoanResponse,
    LoanUpdateMetadataRequest,
    RepaymentScheduleQuoteRequest,
)
from services.frappe_client import FrappeApiClient

logger = getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["mcp-tools"])

ACTIVE_LOAN_STATUSES = ["Disbursed", "Partially Disbursed", "Active"]
MONETARY_CARD_KEYS = {
    "total_disbursed",
    "total_sanctioned_amount",
    "total_shortfall_amount",
    "total_repayment",
    "total_write_off",
}
APPLICANT_TYPES = ["Customer", "Employee"]
REPAYMENT_METHODS = ["Repay Fixed Amount per Period", "Repay Over Number of Periods"]
REPAYMENT_FREQUENCIES = ["Monthly", "Daily", "Weekly", "Bi-Weekly", "Quarterly", "One Time"]


def _today_timespan_filters(doctype: str) -> list[list]:
    return [[doctype, "docstatus", "=", "1"], [doctype, "creation", "Timespan", "today"]]


def _submitted_status_filters(doctype: str, fieldname: str, operator: str, value) -> list[list]:
    return [[doctype, "docstatus", "=", "1"], [doctype, fieldname, operator, value]]


def _sum_rows(rows: list[dict], fieldname: str) -> float:
    return sum(float(row.get(fieldname) or 0) for row in rows)


def _currency_prefix(currency: str | None) -> str:
    if currency == "CHF":
        return "Fr"
    return currency or ""


def _format_card_value(key: str, value: float | int, currency_prefix: str) -> str:
    if key in MONETARY_CARD_KEYS:
        amount = f"{float(value or 0):,.2f}"
        return f"{currency_prefix} {amount}".strip() if currency_prefix else amount
    return str(int(value or 0))


def _card_tone(key: str) -> str:
    if key in {"new_loans", "active_loans", "open_loan_applications", "new_loan_applications"}:
        return "accent"
    if key in {"total_disbursed", "total_sanctioned_amount", "total_repayment"}:
        return "success"
    if key == "total_write_off":
        return "danger"
    if key in {"applicants_with_unpaid_shortfall", "total_shortfall_amount"}:
        return "warning"
    return "default"


def _clean_server_error(raw_error: Exception | str) -> str:
    text = str(raw_error)
    if not text:
        return "Unknown error"
    try:
        decoded = loads(text)
        if isinstance(decoded, dict):
            if decoded.get("message"):
                return str(decoded["message"])
            if decoded.get("exception"):
                return str(decoded["exception"])
    except (JSONDecodeError, TypeError):
        pass
    return text


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
        return await frappe_client.create_doc(
            "Customer",
            payload.model_dump(exclude_none=True),
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
        data = await frappe_client.list_docs(
            "Company",
            fields=["name", "company_name", "default_currency", "country"],
            limit_page_length=limit_page_length,
            order_by="modified desc",
        )
        return {"data": data}
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
        filters: list[list] = []
        if company:
            filters.append(["Loan Product", "company", "=", company])

        data = await frappe_client.list_docs(
            "Loan Product",
            fields=[
                "name",
                "company",
                "payment_account",
                "loan_account",
                "interest_income_account",
                "penalty_income_account",
                "rate_of_interest",
            ],
            filters=filters or None,
            limit_page_length=limit_page_length,
            order_by="modified desc",
        )
        return {"data": data}
    except Exception as exc:
        logger.exception("Loan product list failed")
        raise HTTPException(status_code=400, detail=f"Unable to list loan products: {exc}") from exc


@router.get("/loans/prepare", operation_id="prepare_new_loan", summary="Prepare new loan", response_model=PrepareNewLoanResponse)
async def prepare_new_loan(
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        companies = await frappe_client.list_docs(
            "Company",
            fields=["name", "company_name", "default_currency", "country"],
            limit_page_length=50,
            order_by="modified desc",
        )
        default_company = companies[0]["name"] if companies else None
        customers_task = frappe_client.list_docs(
            "Customer",
            fields=["name", "customer_name"],
            limit_page_length=100,
            order_by="modified desc",
        )
        loan_products_task = frappe_client.list_docs(
            "Loan Product",
            fields=["name", "company", "rate_of_interest", "maximum_loan_amount"],
            filters=[["Loan Product", "company", "=", default_company]] if default_company else None,
            limit_page_length=100,
            order_by="modified desc",
        )
        customers, loan_products = await asyncio.gather(customers_task, loan_products_task)

        default_product = loan_products[0] if loan_products else {}
        posting_date = datetime.now(UTC).date().isoformat()
        defaults = {
            "applicant_type": "Customer",
            "applicant": "",
            "company": default_company,
            "posting_date": posting_date,
            "loan_product": default_product.get("name"),
            "loan_amount": None,
            "rate_of_interest": default_product.get("rate_of_interest"),
            "penalty_charges_rate": None,
            "repayment_frequency": "Monthly",
            "repayment_method": "Repay Over Number of Periods",
            "repayment_periods": 12,
            "repayment_start_date": posting_date,
            "is_secured_loan": 0,
            "is_term_loan": 1,
            "auto_create_disbursement_on_loan_booking": 0,
        }
        preview = {
            "title": "New Loan Preview",
            "applicant": defaults["applicant"] or "Select applicant",
            "company": defaults["company"] or "Select company",
            "loan_product": defaults["loan_product"] or "Select loan product",
            "posting_date": defaults["posting_date"],
        }
        return {
            "view": "prepare_new_loan",
            "generated_at": datetime.now(UTC).isoformat(),
            "defaults": defaults,
            "options": {
                "applicant_types": APPLICANT_TYPES,
                "repayment_methods": REPAYMENT_METHODS,
                "repayment_frequencies": REPAYMENT_FREQUENCIES,
                "companies": companies,
                "customers": customers,
                "loan_products": loan_products,
            },
            "preview": preview,
            "warnings": [],
        }
    except Exception as exc:
        logger.exception("Prepare new loan failed")
        raise HTTPException(status_code=400, detail=f"Unable to prepare new loan: {exc}") from exc


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


@router.post("/loans", operation_id="create_loan", summary="Create and submit loan", response_model=LoanMutationResponse)
async def create_loan(
    payload: LoanCreateRequest,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        created_loan = await frappe_client.create_doc(
            "Loan",
            payload.model_dump(exclude_none=True),
        )
    except Exception as exc:
        logger.exception("Loan create failed")
        raise HTTPException(status_code=400, detail=f"Unable to create loan: {exc}") from exc

    try:
        submitted_loan = await frappe_client.submit_doc(created_loan)
        return {
            "success": True,
            "submitted": True,
            "created_draft": False,
            "loan_name": submitted_loan.get("name") or created_loan.get("name"),
            "message": "Loan created and submitted successfully.",
            "loan": submitted_loan,
        }
    except Exception as exc:
        logger.exception("Loan submit after create failed")
        draft_loan = created_loan
        loan_name = created_loan.get("name")
        if loan_name:
            try:
                draft_loan = await frappe_client.get_doc("Loan", loan_name)
            except Exception:
                logger.warning("Unable to refresh draft loan after submit failure", exc_info=True)
        return {
            "success": False,
            "submitted": False,
            "created_draft": True,
            "loan_name": loan_name,
            "message": "Loan draft created, but submission failed.",
            "error": _clean_server_error(exc),
            "loan": draft_loan,
        }


@router.post("/loans/{loan_name}/submit", operation_id="submit_loan", summary="Submit draft loan", response_model=LoanMutationResponse)
async def submit_loan(
    loan_name: str,
    frappe_client: FrappeApiClient = Depends(get_frappe_client),
):
    try:
        loan_doc = await frappe_client.get_doc("Loan", loan_name)
    except Exception as exc:
        logger.exception("Loan fetch before submit failed")
        raise HTTPException(status_code=404, detail=f"Unable to fetch loan for submission: {exc}") from exc

    if int(loan_doc.get("docstatus") or 0) == 1:
        return {
            "success": True,
            "submitted": True,
            "created_draft": False,
            "already_submitted": True,
            "loan_name": loan_name,
            "message": "Loan is already submitted.",
            "loan": loan_doc,
        }

    try:
        submitted_loan = await frappe_client.submit_doc(loan_doc)
        return {
            "success": True,
            "submitted": True,
            "created_draft": False,
            "loan_name": submitted_loan.get("name") or loan_name,
            "message": "Loan submitted successfully.",
            "loan": submitted_loan,
        }
    except Exception as exc:
        logger.exception("Loan submit failed")
        refreshed_loan = loan_doc
        try:
            refreshed_loan = await frappe_client.get_doc("Loan", loan_name)
        except Exception:
            logger.warning("Unable to refresh loan after submit failure", exc_info=True)
        return {
            "success": False,
            "submitted": False,
            "created_draft": True,
            "loan_name": loan_name,
            "message": "Loan submission failed.",
            "error": _clean_server_error(exc),
            "loan": refreshed_loan,
        }


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


@router.get("/loans/{loan_name}/dashboard-summary", operation_id="get_loan_summary", summary="Get dashboard-style loan summary")
async def get_loan_summary(
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
        logger.exception("Loan summary failed")
        raise HTTPException(status_code=400, detail=f"Unable to build loan summary: {exc}") from exc


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
        companies_task = frappe_client.list_docs(
            "Company",
            fields=["default_currency"],
            limit_page_length=1,
            order_by="modified desc",
        )
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
            filters=[["Loan", "docstatus", "=", "1"], ["Loan", "status", "in", ACTIVE_LOAN_STATUSES]],
            limit_page_length=200,
            order_by="posting_date desc",
        )
        new_loans_task = frappe_client.get_count("Loan", filters=_today_timespan_filters("Loan"))
        active_loan_count_task = frappe_client.get_count(
            "Loan",
            filters=[["Loan", "docstatus", "=", "1"], ["Loan", "status", "in", ACTIVE_LOAN_STATUSES]],
        )
        open_loan_applications_task = frappe_client.get_count(
            "Loan Application",
            filters=_submitted_status_filters("Loan Application", "status", "=", "Open"),
        )
        new_loan_applications_task = frappe_client.get_count(
            "Loan Application",
            filters=_today_timespan_filters("Loan Application"),
        )
        closed_loan_count_task = frappe_client.get_count(
            "Loan",
            filters=_submitted_status_filters("Loan", "status", "=", "Closed"),
        )
        active_securities_task = frappe_client.get_count(
            "Loan Security",
            filters=[["Loan Security", "disabled", "=", 0]],
        )
        sanctioned_loans_task = frappe_client.list_docs(
            "Loan",
            fields=["loan_amount"],
            filters=_submitted_status_filters("Loan", "status", "=", "Sanctioned"),
            limit_page_length=1000,
            order_by="modified desc",
        )
        disbursements_task = frappe_client.list_docs(
            "Loan Disbursement",
            fields=["disbursed_amount"],
            filters=[["Loan Disbursement", "docstatus", "=", "1"]],
            limit_page_length=1000,
            order_by="modified desc",
        )
        repayments_task = frappe_client.list_docs(
            "Loan Repayment",
            fields=["amount_paid"],
            filters=[["Loan Repayment", "docstatus", "=", "1"]],
            limit_page_length=1000,
            order_by="modified desc",
        )
        write_offs_task = frappe_client.list_docs(
            "Loan Write Off",
            fields=["write_off_amount"],
            filters=[["Loan Write Off", "docstatus", "=", "1"]],
            limit_page_length=1000,
            order_by="modified desc",
        )
        shortfalls_task = frappe_client.list_docs(
            "Loan Security Shortfall",
            fields=["loan", "shortfall_amount", "status"],
            filters=[["Loan Security Shortfall", "status", "=", "Pending"]],
            limit_page_length=1000,
            order_by="modified desc",
        )

        (
            companies,
            portfolio_loans,
            new_loans,
            active_loan_count,
            open_loan_applications,
            new_loan_applications,
            closed_loan_count,
            active_securities,
            sanctioned_loans,
            disbursements,
            repayments,
            write_offs,
            shortfalls,
        ) = await asyncio.gather(
            companies_task,
            portfolio_loans_task,
            new_loans_task,
            active_loan_count_task,
            open_loan_applications_task,
            new_loan_applications_task,
            closed_loan_count_task,
            active_securities_task,
            sanctioned_loans_task,
            disbursements_task,
            repayments_task,
            write_offs_task,
            shortfalls_task,
        )

        shortfall_loan_names = sorted({row.get("loan") for row in shortfalls if row.get("loan")})
        shortfall_loans = (
            await frappe_client.list_docs(
                "Loan",
                fields=["name", "applicant"],
                filters=[["Loan", "name", "in", shortfall_loan_names]],
                limit_page_length=max(len(shortfall_loan_names), 1),
                order_by="modified desc",
            )
            if shortfall_loan_names
            else []
        )

        generated_at = datetime.now(UTC).isoformat()
        currency_prefix = _currency_prefix((companies[0].get("default_currency") if companies else None))

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

        applicants_with_unpaid_shortfall = len({row.get("applicant") for row in shortfall_loans if row.get("applicant")})
        cards = {
            "new_loans": new_loans,
            "active_loans": active_loan_count,
            "closed_loans": closed_loan_count,
            "total_disbursed": _sum_rows(disbursements, "disbursed_amount"),
            "open_loan_applications": open_loan_applications,
            "new_loan_applications": new_loan_applications,
            "total_sanctioned_amount": _sum_rows(sanctioned_loans, "loan_amount"),
            "active_securities": active_securities,
            "applicants_with_unpaid_shortfall": applicants_with_unpaid_shortfall,
            "total_shortfall_amount": _sum_rows(shortfalls, "shortfall_amount"),
            "total_repayment": _sum_rows(repayments, "amount_paid"),
            "total_write_off": _sum_rows(write_offs, "write_off_amount"),
        }

        hero_card_definitions = [
            ("new_loans", "New Loans"),
            ("active_loans", "Active Loans"),
            ("closed_loans", "Closed Loans"),
            ("total_disbursed", "Total Disbursed"),
            ("open_loan_applications", "Open Loan Applications"),
            ("new_loan_applications", "New Loan Applications"),
            ("total_sanctioned_amount", "Total Sanctioned Amount"),
            ("active_securities", "Active Securities"),
            ("applicants_with_unpaid_shortfall", "Applicants With Unpaid Shortfall"),
            ("total_shortfall_amount", "Total Shortfall Amount"),
            ("total_repayment", "Total Repayment"),
            ("total_write_off", "Total Write Off"),
        ]

        return {
            "generated_at": generated_at,
            "overview": {
                "generated_at": generated_at,
                "cards": cards,
            },
            "hero_cards": [
                {
                    "key": key,
                    "label": label,
                    "value": _format_card_value(key, cards.get(key, 0), currency_prefix),
                    "tone": _card_tone(key),
                }
                for key, label in hero_card_definitions
            ],
            "recent_loans": portfolio_loans[:5],
            "top_outstanding": top_outstanding,
            "outstanding_totals": outstanding_totals,
            "actions": [
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
