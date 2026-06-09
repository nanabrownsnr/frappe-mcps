import frappe
from frappe import _


@frappe.whitelist()
def get_dashboard_overview():
	active_loans = frappe.db.count(
		"Loan",
		{"docstatus": 1, "status": ["in", ["Disbursed", "Partially Disbursed", "Active"]]},
	)
	open_loan_applications = frappe.db.count(
		"Loan Application", {"docstatus": 1, "status": "Open"}
	)
	closed_loans = frappe.db.count("Loan", {"docstatus": 1, "status": "Closed"})

	total_disbursed_row = frappe.get_all(
		"Loan Disbursement",
		fields=["sum(disbursed_amount) as total_disbursed"],
		filters={"docstatus": 1},
		limit_page_length=1,
	)
	total_repayment_row = frappe.get_all(
		"Loan Repayment",
		fields=["sum(amount_paid) as total_repayment"],
		filters={"docstatus": 1},
		limit_page_length=1,
	)

	return {
		"cards": {
			"active_loans": active_loans,
			"open_loan_applications": open_loan_applications,
			"closed_loans": closed_loans,
			"total_disbursed": (total_disbursed_row[0].total_disbursed if total_disbursed_row else 0) or 0,
			"total_repayment": (total_repayment_row[0].total_repayment if total_repayment_row else 0) or 0,
		}
	}


@frappe.whitelist()
def list_companies(limit_page_length=50):
	return frappe.get_all(
		"Company",
		fields=["name", "company_name", "default_currency", "country"],
		limit_page_length=limit_page_length,
		order_by="modified desc",
	)


@frappe.whitelist()
def list_loan_products(company=None, limit_page_length=50):
	filters = {}
	if company:
		filters["company"] = company

	return frappe.get_all(
		"Loan Product",
		fields=[
			"name",
			"company",
			"rate_of_interest",
			"repayment_schedule_type",
			"maximum_loan_amount",
		],
		filters=filters,
		limit_page_length=limit_page_length,
		order_by="modified desc",
	)


@frappe.whitelist()
def create_customer(
	customer_name,
	customer_type="Individual",
	customer_group="Commercial",
	territory="All Territories",
	mobile_no=None,
	email_id=None,
):
	if not frappe.db.exists("Customer Group", customer_group):
		frappe.throw(_("Customer Group {0} does not exist").format(frappe.bold(customer_group)))

	if territory and not frappe.db.exists("Territory", territory):
		frappe.throw(_("Territory {0} does not exist").format(frappe.bold(territory)))

	customer = frappe.new_doc("Customer")
	customer.customer_name = customer_name
	customer.customer_type = customer_type
	customer.customer_group = customer_group
	customer.territory = territory
	customer.mobile_no = mobile_no
	customer.email_id = email_id
	customer.insert(ignore_permissions=True)
	return customer.as_dict()


@frappe.whitelist()
def create_loan(
	applicant_type,
	applicant,
	company,
	loan_product,
	posting_date=None,
	loan_amount=None,
	rate_of_interest=None,
	repayment_method=None,
	repayment_periods=None,
	repayment_start_date=None,
):
	loan = frappe.new_doc("Loan")
	loan.applicant_type = applicant_type
	loan.applicant = applicant
	loan.company = company
	loan.loan_product = loan_product
	if posting_date:
		loan.posting_date = posting_date
	if loan_amount is not None:
		loan.loan_amount = loan_amount
	if rate_of_interest is not None:
		loan.rate_of_interest = rate_of_interest
	if repayment_method:
		loan.repayment_method = repayment_method
	if repayment_periods is not None:
		loan.repayment_periods = repayment_periods
	if repayment_start_date:
		loan.repayment_start_date = repayment_start_date
	loan.insert(ignore_permissions=True)
	return loan.as_dict()
