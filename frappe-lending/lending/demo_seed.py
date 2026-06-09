from __future__ import annotations

import frappe
from frappe.utils import add_months, now_datetime

from erpnext.setup.setup_wizard.operations.install_fixtures import set_global_defaults
from erpnext.setup.utils import enable_all_roles_and_domains
from lending.tests.test_utils import (
	add_or_update_loan_charges,
	create_loan,
	create_loan_accounts,
	create_loan_product,
	create_repayment_entry,
	loan_classification_ranges,
	make_loan_disbursement_entry,
	set_loan_accrual_frequency,
	set_loan_settings_in_company,
	setup_loan_demand_offset_order,
)


def _ensure_base_setup():
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = now_datetime().year

	if not frappe.get_list("Company"):
		setup_complete(
			{
				"currency": "INR",
				"full_name": "Administrator",
				"company_name": "_Test Company",
				"timezone": "Asia/Kolkata",
				"company_abbr": "_TC",
				"industry": "Manufacturing",
				"country": "India",
				"fy_start_date": f"{year}-01-01",
				"fy_end_date": f"{year}-12-31",
				"language": "english",
				"company_tagline": "Demo Lending Company",
				"email": "admin@example.com",
				"password": "admin",
				"chart_of_accounts": "Standard",
			}
		)

	set_global_defaults(
		{
			"currency": "INR",
			"company_name": "_Test Company",
			"country": "India",
		}
	)
	enable_all_roles_and_domains()
	set_loan_settings_in_company()
	create_loan_accounts()
	setup_loan_demand_offset_order()
	set_loan_accrual_frequency("Monthly")
	loan_classification_ranges()


def _ensure_loan_products():
	products = [
		("Personal Loan", 500000, 8.4, "Monthly as per repayment start date", None),
		("Term Loan Product 4", 3000000, 25, "Monthly as per cycle date", None),
		("Stock Loan", 2000000, 13.5, "Monthly as per repayment start date", None),
		("Demand Loan", 2000000, 13.5, None, None),
	]

	for product_name, max_amount, rate, schedule_type, repayment_date_on in products:
		if product_name == "Demand Loan":
			create_loan_product(
				product_name,
				product_name,
				max_amount,
				rate,
				25,
				0,
				5,
				collection_offset_sequence_for_standard_asset="Test Demand Loan Loan Demand Offset Order",
				collection_offset_sequence_for_sub_standard_asset=None,
				collection_offset_sequence_for_written_off_asset=None,
				collection_offset_sequence_for_settlement_collection=None,
			)
			continue

		create_loan_product(
			product_name,
			product_name,
			max_amount,
			rate,
			repayment_schedule_type=schedule_type,
			repayment_date_on=repayment_date_on,
			collection_offset_sequence_for_standard_asset="Test EMI Based Standard Loan Demand Offset Order"
			if product_name == "Stock Loan"
			else None,
		)

	add_or_update_loan_charges("Term Loan Product 4")


def _ensure_customer(customer_name: str) -> str:
	if not frappe.db.exists("Customer", customer_name):
		customer_group = (
			"Commercial"
			if frappe.db.exists("Customer Group", "Commercial")
			else frappe.get_all("Customer Group", pluck="name", limit=1)[0]
		)
		territory = (
			"All Territories"
			if frappe.db.exists("Territory", "All Territories")
			else frappe.get_all("Territory", pluck="name", limit=1)[0]
		)
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": customer_name,
				"customer_type": "Individual",
				"customer_group": customer_group,
				"territory": territory,
			}
		).insert(ignore_permissions=True)
	return customer_name


def _ensure_term_loan(
	applicant: str,
	loan_product: str,
	loan_amount: float,
	posting_date: str,
	repayment_start_date: str,
	repayment_periods: int,
	repayment_amount: float,
):
	existing = frappe.get_all(
		"Loan",
		filters={
			"applicant": applicant,
			"loan_product": loan_product,
			"posting_date": posting_date,
			"company": "_Test Company",
		},
		fields=["name", "docstatus"],
		limit=1,
	)
	if existing:
		loan = frappe.get_doc("Loan", existing[0].name)
	else:
		loan = create_loan(
			applicant=applicant,
			loan_product=loan_product,
			loan_amount=loan_amount,
			repayment_method="Repay Over Number of Periods",
			repayment_periods=repayment_periods,
			repayment_start_date=repayment_start_date,
			posting_date=posting_date,
		)

	if loan.docstatus == 0:
		loan.submit()

	disbursement = frappe.get_all(
		"Loan Disbursement",
		filters={"against_loan": loan.name, "docstatus": 1},
		fields=["name"],
		limit=1,
	)
	if not disbursement:
		disbursement_doc = make_loan_disbursement_entry(
			loan.name,
			loan_amount,
			disbursement_date=posting_date,
			repayment_start_date=repayment_start_date,
		)
	else:
		disbursement_doc = frappe.get_doc("Loan Disbursement", disbursement[0].name)

	repayment = frappe.get_all(
		"Loan Repayment",
		filters={"against_loan": loan.name, "docstatus": 1},
		fields=["name"],
		limit=1,
	)
	if not repayment:
		repayment_doc = create_repayment_entry(
			loan=loan.name,
			value_date=add_months(repayment_start_date, 1),
			paid_amount=repayment_amount,
			loan_disbursement=disbursement_doc.name,
		)
		repayment_doc.submit()

	return loan.name


def _ensure_demo_records():
	customers = [
		_ensure_customer("_Test Loan Customer"),
		_ensure_customer("_Test Loan Customer 1"),
		_ensure_customer("_Test Loan Customer 2"),
	]

	_ensure_term_loan(
		applicant=customers[0],
		loan_product="Personal Loan",
		loan_amount=120000,
		posting_date="2026-01-10",
		repayment_start_date="2026-02-10",
		repayment_periods=12,
		repayment_amount=15000,
	)
	_ensure_term_loan(
		applicant=customers[1],
		loan_product="Term Loan Product 4",
		loan_amount=250000,
		posting_date="2026-02-05",
		repayment_start_date="2026-03-05",
		repayment_periods=24,
		repayment_amount=22000,
	)
	_ensure_term_loan(
		applicant=customers[2],
		loan_product="Stock Loan",
		loan_amount=180000,
		posting_date="2026-03-01",
		repayment_start_date="2026-04-01",
		repayment_periods=18,
		repayment_amount=12000,
	)


def run():
	frappe.flags.in_test = True
	_ensure_base_setup()
	_ensure_loan_products()
	_ensure_demo_records()
	frappe.db.commit()
	return {
		"company_count": frappe.db.count("Company"),
		"customer_count": frappe.db.count("Customer"),
		"loan_product_count": frappe.db.count("Loan Product"),
		"loan_count": frappe.db.count("Loan"),
		"loan_disbursement_count": frappe.db.count("Loan Disbursement"),
		"loan_repayment_count": frappe.db.count("Loan Repayment"),
	}
