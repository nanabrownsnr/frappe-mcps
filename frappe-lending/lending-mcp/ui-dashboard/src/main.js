import {
  App,
  applyDocumentTheme,
  applyHostFonts,
  applyHostStyleVariables,
} from "@modelcontextprotocol/ext-apps";
import "./styles.css";
import brandLogo from "./world-business-lenders_logo-185-100px.png";

const TOOL_DASHBOARD = "dashboard_loan_summary";
const TOOL_PREPARE = "prepare_new_loan";
const TOOL_CREATE = "create_loan";
const TOOL_COMPANIES = "company_list";
const TOOL_CUSTOMERS = "customer_list";
const TOOL_LOAN_PRODUCTS = "loan_product_list";

const state = {
  view: "dashboard",
  summary: null,
  prepare: null,
  options: {
    companies: [],
    customers: [],
    loan_products: [],
    applicant_types: [],
    repayment_methods: [],
    repayment_frequencies: [],
  },
  form: {},
};

const appRoot = document.getElementById("app");
const pageTitleEl = document.getElementById("page-title");
const subtitleEl = document.getElementById("subtitle");
const errorBannerEl = document.getElementById("error-banner");
const statusBannerEl = document.getElementById("status-banner");
const primaryActionBtn = document.getElementById("primary-action");
const refreshOptionsBtn = document.getElementById("refresh-options");
const brandLogoEl = document.getElementById("brand-logo");
const dashboardViewEl = document.getElementById("dashboard-view");
const prepareViewEl = document.getElementById("prepare-view");
const heroCardsEl = document.getElementById("hero-cards");
const previewCardEl = document.getElementById("preview-card");

const fieldEls = {
  applicant_type: document.getElementById("field-applicant-type"),
  company: document.getElementById("field-company"),
  applicant: document.getElementById("field-applicant"),
  posting_date: document.getElementById("field-posting-date"),
  loan_product: document.getElementById("field-loan-product"),
  loan_amount: document.getElementById("field-loan-amount"),
  rate_of_interest: document.getElementById("field-rate-of-interest"),
  penalty_charges_rate: document.getElementById("field-penalty-charges-rate"),
  repayment_method: document.getElementById("field-repayment-method"),
  repayment_frequency: document.getElementById("field-repayment-frequency"),
  repayment_periods: document.getElementById("field-repayment-periods"),
  repayment_start_date: document.getElementById("field-repayment-start-date"),
  is_term_loan: document.getElementById("field-is-term-loan"),
  is_secured_loan: document.getElementById("field-is-secured-loan"),
  auto_create_disbursement_on_loan_booking: document.getElementById("field-auto-disbursement"),
};

const mcpApp = new App({ name: "Lending Dashboard", version: "1.1.0" });

function extractToolPayload(result) {
  if (!result) return null;
  if (result.structuredContent) return result.structuredContent;
  if (result.data) return result.data;
  const textPayload = result.content?.find((item) => item.type === "text")?.text;
  if (!textPayload) return null;
  try {
    return JSON.parse(textPayload);
  } catch {
    return null;
  }
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function formatMoney(value) {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return "—";
  return numeric.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderError(message) {
  if (!message) {
    errorBannerEl.classList.add("hidden");
    errorBannerEl.textContent = "";
    return;
  }
  errorBannerEl.textContent = message;
  errorBannerEl.classList.remove("hidden");
}

function renderStatus(message, tone = "success") {
  if (!message) {
    statusBannerEl.className = "status hidden";
    statusBannerEl.textContent = "";
    return;
  }
  statusBannerEl.textContent = message;
  statusBannerEl.className = `status status-${tone}`;
}

function renderHeroCards(cards = []) {
  if (!cards.length) {
    heroCardsEl.innerHTML = `<div class="empty-card">No headline metrics available.</div>`;
    return;
  }

  heroCardsEl.innerHTML = cards
    .map(
      (card) => `
        <article class="card card-${card.tone || "default"}">
          <div class="card-header">
            <p class="card-label">${card.label}</p>
            <span class="card-menu">…</span>
          </div>
          <p class="card-value">${card.value}</p>
        </article>
      `,
    )
    .join("");
}

function setView(view) {
  state.view = view;
  const isPrepare = view === "prepare";
  dashboardViewEl.classList.toggle("hidden", isPrepare);
  prepareViewEl.classList.toggle("hidden", !isPrepare);
  pageTitleEl.textContent = isPrepare ? "Prepare New Loan" : "Loan Dashboard";
  primaryActionBtn.textContent = isPrepare ? "Create Loan" : "Update Dashboard";
}

function optionLabel(option, fallbackKey = "name") {
  if (typeof option === "string") return option;
  return option.customer_name || option.company_name || option[fallbackKey] || option.label || "";
}

function optionValue(option) {
  if (typeof option === "string") return option;
  return option.name || option.value || "";
}

function setSelectOptions(selectEl, options, selectedValue, { includeEmpty = false, emptyLabel = "Select" } = {}) {
  const normalized = [...options];
  if (includeEmpty) {
    normalized.unshift({ name: "", label: emptyLabel });
  }
  selectEl.innerHTML = normalized
    .map((option) => {
      const value = optionValue(option);
      const label = optionLabel(option);
      const selected = String(value || "") === String(selectedValue || "") ? "selected" : "";
      return `<option value="${String(value)}" ${selected}>${label}</option>`;
    })
    .join("");
}

function coerceCheckboxValue(checked) {
  return checked ? 1 : 0;
}

function syncFormFromDom() {
  state.form = {
    applicant_type: fieldEls.applicant_type.value,
    company: fieldEls.company.value,
    applicant: fieldEls.applicant.value,
    posting_date: fieldEls.posting_date.value,
    loan_product: fieldEls.loan_product.value,
    loan_amount: fieldEls.loan_amount.value ? Number(fieldEls.loan_amount.value) : null,
    rate_of_interest: fieldEls.rate_of_interest.value ? Number(fieldEls.rate_of_interest.value) : null,
    penalty_charges_rate: fieldEls.penalty_charges_rate.value ? Number(fieldEls.penalty_charges_rate.value) : null,
    repayment_method: fieldEls.repayment_method.value,
    repayment_frequency: fieldEls.repayment_frequency.value,
    repayment_periods: fieldEls.repayment_periods.value ? Number(fieldEls.repayment_periods.value) : null,
    repayment_start_date: fieldEls.repayment_start_date.value,
    is_term_loan: coerceCheckboxValue(fieldEls.is_term_loan.checked),
    is_secured_loan: coerceCheckboxValue(fieldEls.is_secured_loan.checked),
    auto_create_disbursement_on_loan_booking: coerceCheckboxValue(fieldEls.auto_create_disbursement_on_loan_booking.checked),
  };
  renderPreview();
}

function applyProductDefaults() {
  const selectedProduct = state.options.loan_products.find((product) => product.name === state.form.loan_product);
  if (!selectedProduct) return;
  if ((state.form.rate_of_interest === null || state.form.rate_of_interest === "") && selectedProduct.rate_of_interest != null) {
    state.form.rate_of_interest = Number(selectedProduct.rate_of_interest);
    fieldEls.rate_of_interest.value = state.form.rate_of_interest;
  }
}

function renderPreview() {
  const form = state.form;
  const missing = [];
  ["company", "applicant", "loan_product", "posting_date"].forEach((key) => {
    if (!form[key]) missing.push(key.replaceAll("_", " "));
  });
  previewCardEl.innerHTML = `
    <div class="preview-grid">
      <div><span class="preview-label">Applicant</span><strong>${form.applicant || "Select applicant"}</strong></div>
      <div><span class="preview-label">Company</span><strong>${form.company || "Select company"}</strong></div>
      <div><span class="preview-label">Loan Product</span><strong>${form.loan_product || "Select loan product"}</strong></div>
      <div><span class="preview-label">Loan Amount</span><strong>${form.loan_amount != null ? formatMoney(form.loan_amount) : "Enter amount"}</strong></div>
      <div><span class="preview-label">Interest Rate</span><strong>${form.rate_of_interest != null ? `${form.rate_of_interest}%` : "Set rate"}</strong></div>
      <div><span class="preview-label">Repayment</span><strong>${form.repayment_method || "Choose method"}${form.repayment_periods ? ` • ${form.repayment_periods} periods` : ""}</strong></div>
    </div>
    ${missing.length ? `<p class="preview-warning">Missing: ${missing.join(", ")}.</p>` : `<p class="preview-success">Ready to create and submit when you are.</p>`}
  `;
}

function renderPrepare(payload) {
  state.prepare = payload;
  state.options = {
    ...state.options,
    ...(payload.options || {}),
  };
  state.form = { ...(payload.defaults || {}) };
  setView("prepare");
  subtitleEl.textContent = `Prepared ${formatDate(payload.generated_at)}. Review the details, then create the loan.`;

  setSelectOptions(fieldEls.applicant_type, state.options.applicant_types || [], state.form.applicant_type);
  setSelectOptions(fieldEls.company, state.options.companies || [], state.form.company);
  setSelectOptions(fieldEls.applicant, state.options.customers || [], state.form.applicant, {
    includeEmpty: true,
    emptyLabel: "Select applicant",
  });
  setSelectOptions(fieldEls.loan_product, state.options.loan_products || [], state.form.loan_product, {
    includeEmpty: true,
    emptyLabel: "Select loan product",
  });
  setSelectOptions(fieldEls.repayment_method, state.options.repayment_methods || [], state.form.repayment_method);
  setSelectOptions(fieldEls.repayment_frequency, state.options.repayment_frequencies || [], state.form.repayment_frequency);

  fieldEls.posting_date.value = state.form.posting_date || "";
  fieldEls.loan_amount.value = state.form.loan_amount ?? "";
  fieldEls.rate_of_interest.value = state.form.rate_of_interest ?? "";
  fieldEls.penalty_charges_rate.value = state.form.penalty_charges_rate ?? "";
  fieldEls.repayment_periods.value = state.form.repayment_periods ?? "";
  fieldEls.repayment_start_date.value = state.form.repayment_start_date || "";
  fieldEls.is_term_loan.checked = Boolean(state.form.is_term_loan);
  fieldEls.is_secured_loan.checked = Boolean(state.form.is_secured_loan);
  fieldEls.auto_create_disbursement_on_loan_booking.checked = Boolean(
    state.form.auto_create_disbursement_on_loan_booking,
  );

  renderPreview();
}

function renderDashboard(payload) {
  state.summary = payload;
  setView("dashboard");
  renderHeroCards(payload.hero_cards || []);
  subtitleEl.textContent = `Last updated ${formatDate(payload.generated_at)}.`;
}

function renderPayload(payload) {
  renderError("");
  renderStatus("");
  if (!payload) {
    renderError("The tool returned no structured content.");
    return;
  }
  if (payload.view === "prepare_new_loan") {
    renderPrepare(payload);
    return;
  }
  renderDashboard(payload);
}

function handleHostContextChanged(context) {
  if (context.theme) applyDocumentTheme(context.theme);
  if (context.styles?.variables) applyHostStyleVariables(context.styles.variables);
  if (context.styles?.css?.fonts) applyHostFonts(context.styles.css.fonts);
  if (context.safeAreaInsets) {
    appRoot.style.paddingTop = `${context.safeAreaInsets.top + 16}px`;
    appRoot.style.paddingRight = `${context.safeAreaInsets.right + 16}px`;
    appRoot.style.paddingBottom = `${context.safeAreaInsets.bottom + 16}px`;
    appRoot.style.paddingLeft = `${context.safeAreaInsets.left + 16}px`;
  }
}

async function callDashboardTool() {
  renderError("");
  renderStatus("");
  subtitleEl.textContent = "Loading dashboard summary…";
  try {
    const result = await mcpApp.callServerTool({ name: TOOL_DASHBOARD, arguments: {} });
    renderPayload(extractToolPayload(result));
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Dashboard tool call failed.");
  }
}

async function refreshLoanProductsForCompany(company) {
  try {
    const result = await mcpApp.callServerTool({
      name: TOOL_LOAN_PRODUCTS,
      arguments: company ? { company } : {},
    });
    const payload = extractToolPayload(result);
    state.options.loan_products = payload?.data || [];
    setSelectOptions(fieldEls.loan_product, state.options.loan_products, state.form.loan_product, {
      includeEmpty: true,
      emptyLabel: "Select loan product",
    });
    if (!state.options.loan_products.some((product) => product.name === state.form.loan_product)) {
      state.form.loan_product = state.options.loan_products[0]?.name || "";
      fieldEls.loan_product.value = state.form.loan_product;
      fieldEls.rate_of_interest.value = state.options.loan_products[0]?.rate_of_interest ?? "";
      state.form.rate_of_interest = fieldEls.rate_of_interest.value ? Number(fieldEls.rate_of_interest.value) : null;
    }
    applyProductDefaults();
    renderPreview();
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Unable to load loan products.");
  }
}

async function reloadReferenceData() {
  try {
    renderError("");
    const [companiesResult, customersResult] = await Promise.all([
      mcpApp.callServerTool({ name: TOOL_COMPANIES, arguments: {} }),
      mcpApp.callServerTool({ name: TOOL_CUSTOMERS, arguments: {} }),
    ]);
    state.options.companies = extractToolPayload(companiesResult)?.data || [];
    state.options.customers = extractToolPayload(customersResult)?.data || [];
    setSelectOptions(fieldEls.company, state.options.companies, state.form.company);
    setSelectOptions(fieldEls.applicant, state.options.customers, state.form.applicant, {
      includeEmpty: true,
      emptyLabel: "Select applicant",
    });
    await refreshLoanProductsForCompany(state.form.company);
    renderStatus("Reference data refreshed.");
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Unable to refresh reference data.");
  }
}

function validateForm() {
  syncFormFromDom();
  const required = [
    ["applicant_type", "Applicant type"],
    ["company", "Company"],
    ["applicant", "Applicant"],
    ["posting_date", "Posting date"],
    ["loan_product", "Loan product"],
    ["loan_amount", "Loan amount"],
    ["rate_of_interest", "Rate of interest"],
    ["repayment_method", "Repayment method"],
    ["repayment_periods", "Repayment periods"],
    ["repayment_start_date", "Repayment start date"],
  ];
  const missing = required.filter(([key]) => state.form[key] === "" || state.form[key] == null);
  if (missing.length) {
    throw new Error(`Missing required fields: ${missing.map(([, label]) => label).join(", ")}.`);
  }
}

async function createLoanFromForm() {
  try {
    validateForm();
    renderError("");
    renderStatus("Creating and submitting loan…", "info");
    const result = await mcpApp.callServerTool({ name: TOOL_CREATE, arguments: state.form });
    const payload = extractToolPayload(result) || result;
    if (payload.success) {
      renderStatus(`${payload.message} ${payload.loan_name ? `Loan: ${payload.loan_name}.` : ""}`);
      subtitleEl.textContent = `Created ${payload.loan_name || "loan"} successfully.`;
      return;
    }
    renderStatus(
      `${payload.message} ${payload.loan_name ? `Draft: ${payload.loan_name}.` : ""} ${payload.error || ""}`.trim(),
      "warning",
    );
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Loan creation failed.");
  }
}

function handlePrimaryAction() {
  if (state.view === "prepare") {
    createLoanFromForm();
    return;
  }
  callDashboardTool();
}

function bindFieldEvents() {
  Object.entries(fieldEls).forEach(([key, element]) => {
    const eventName = element.type === "checkbox" ? "change" : "input";
    element.addEventListener(eventName, () => {
      if (key === "company") {
        syncFormFromDom();
        refreshLoanProductsForCompany(fieldEls.company.value);
        return;
      }
      if (key === "loan_product") {
        syncFormFromDom();
        const selectedProduct = state.options.loan_products.find((product) => product.name === fieldEls.loan_product.value);
        if (selectedProduct?.rate_of_interest != null) {
          fieldEls.rate_of_interest.value = selectedProduct.rate_of_interest;
        }
        syncFormFromDom();
        return;
      }
      syncFormFromDom();
    });
  });
}

mcpApp.onhostcontextchanged = handleHostContextChanged;
mcpApp.ontoolinput = () => {
  renderError("");
  renderStatus("");
};
mcpApp.ontoolresult = (result) => {
  renderPayload(extractToolPayload(result));
};
mcpApp.ontoolcancelled = () => {
  renderError("The tool call was cancelled.");
};
mcpApp.onerror = (error) => {
  renderError(error instanceof Error ? error.message : "Unexpected app error.");
};

if (brandLogoEl) {
  brandLogoEl.src = brandLogo;
}

primaryActionBtn.addEventListener("click", handlePrimaryAction);
refreshOptionsBtn?.addEventListener("click", reloadReferenceData);
bindFieldEvents();

mcpApp.connect().then(() => {
  const context = mcpApp.getHostContext();
  if (context) handleHostContextChanged(context);
});
