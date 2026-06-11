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
    penalty_charges_rate: float | None = None
    repayment_frequency: str | None = None
    repayment_method: str | None = None
    repayment_periods: int | None = None
    repayment_start_date: str | None = None
    is_secured_loan: int | None = None
    is_term_loan: int | None = None
    auto_create_disbursement_on_loan_booking: int | None = None


class PrepareNewLoanResponse(BaseModel):
    view: str
    generated_at: str
    defaults: dict
    options: dict
    preview: dict
    warnings: list[str] = Field(default_factory=list)


class LoanMutationResponse(BaseModel):
    success: bool
    submitted: bool
    created_draft: bool = False
    already_submitted: bool = False
    loan_name: str | None = None
    message: str
    error: str | None = None
    loan: dict | None = None


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
    new_loans: int
    active_loans: int
    open_loan_applications: int
    new_loan_applications: int
    closed_loans: int
    total_disbursed: float
    total_sanctioned_amount: float
    active_securities: int
    applicants_with_unpaid_shortfall: int
    total_shortfall_amount: float
    total_repayment: float
    total_write_off: float


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
