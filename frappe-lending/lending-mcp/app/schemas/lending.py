from pydantic import BaseModel, Field


class CustomerCreateRequest(BaseModel):
    customer_name: str
    customer_type: str = Field(default="Individual")
    customer_group: str = Field(default="Commercial")
    territory: str = Field(default="All Territories")
    mobile_no: str | None = None
    email_id: str | None = None


class CustomerUpdateRequest(BaseModel):
    customer_name: str | None = None
    mobile_no: str | None = None
    email_id: str | None = None
    customer_group: str | None = None
    territory: str | None = None


class CustomerListResponse(BaseModel):
    data: list[dict]


class LoanCreateRequest(BaseModel):
    applicant_type: str = Field(default="Customer")
    applicant: str
    company: str
    loan_product: str
    posting_date: str | None = None
    loan_amount: float | None = None
    rate_of_interest: float | None = None
    repayment_method: str | None = None
    repayment_periods: int | None = None
    repayment_start_date: str | None = None


class LoanListRequest(BaseModel):
    company: str | None = None
    applicant: str | None = None
    status: list[str] | None = None
    limit_page_length: int = 20
    order_by: str = "modified desc"


class LoanUpdateMetadataRequest(BaseModel):
    manual_npa: int | None = None
    freeze_account: int | None = None
    freeze_date: str | None = None
    freeze_reason: str | None = None
    maximum_limit_amount: float | None = None


class RepaymentScheduleQuoteRequest(BaseModel):
    loan_product: str
    loan_amount: float
    rate_of_interest: float
    tenure: int
    repayment_frequency: str | None = "Monthly"
    repayment_start_date: str | None = None


class DueDetailsResponse(BaseModel):
    data: dict


class DashboardOverviewCards(BaseModel):
    active_loans: int
    open_loan_applications: int
    closed_loans: int
    total_disbursed: float
    total_repayment: float


class DashboardOverviewResponse(BaseModel):
    generated_at: str | None = None
    cards: DashboardOverviewCards


class DashboardHeroCard(BaseModel):
    key: str
    label: str
    value: str
    tone: str = "default"


class DashboardAction(BaseModel):
    label: str
    tool: str
    description: str


class LoanDashboardSummaryResponse(BaseModel):
    generated_at: str
    overview: DashboardOverviewResponse
    hero_cards: list[DashboardHeroCard]
    recent_loans: list[dict]
    top_outstanding: list[dict]
    outstanding_totals: dict
    actions: list[DashboardAction]


class LoanOutstandingReportRequest(BaseModel):
    company: str | None = None
    applicant: str | None = None
    branch: str | None = None
    posting_date: str | None = None

