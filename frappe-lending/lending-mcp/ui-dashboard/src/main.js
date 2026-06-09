import {
  App,
  applyDocumentTheme,
  applyHostFonts,
  applyHostStyleVariables,
} from "@modelcontextprotocol/ext-apps";
import "./styles.css";

const TOOL_SUMMARY = "dashboard_loan_summary";

const state = {
  lastTool: TOOL_SUMMARY,
  summary: null,
};

const appRoot = document.getElementById("app");
const subtitleEl = document.getElementById("subtitle");
const errorBannerEl = document.getElementById("error-banner");
const heroCardsEl = document.getElementById("hero-cards");
const topOutstandingEl = document.getElementById("top-outstanding");
const recentLoansEl = document.getElementById("recent-loans");
const overviewCardsEl = document.getElementById("overview-cards");
const outstandingTotalEl = document.getElementById("outstanding-total");
const recentCountEl = document.getElementById("recent-count");
const generatedAtEl = document.getElementById("generated-at");
const refreshSummaryBtn = document.getElementById("refresh-summary");

const mcpApp = new App({ name: "Lending Dashboard", version: "1.0.0" });

function formatNumber(value) {
  const numeric = Number(value ?? 0);
  return Number.isFinite(numeric) ? numeric.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0";
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
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

function renderHeroCards(cards = []) {
  if (!cards.length) {
    heroCardsEl.innerHTML = `<div class="empty-card">No headline metrics available.</div>`;
    return;
  }
  heroCardsEl.innerHTML = cards
    .map(
      (card) => `
        <article class="card card-${card.tone || "default"}">
          <p class="card-label">${card.label}</p>
          <p class="card-value">${card.value}</p>
        </article>
      `,
    )
    .join("");
}

function renderSimpleCards(cards) {
  const entries = Object.entries(cards || {});
  if (!entries.length) {
    overviewCardsEl.innerHTML = `<div class="empty-card">No overview metrics available.</div>`;
    return;
  }
  overviewCardsEl.innerHTML = entries
    .map(
      ([key, value]) => `
        <article class="overview-card">
          <p class="card-label">${key.replaceAll("_", " ")}</p>
          <p class="overview-value">${typeof value === "number" ? formatNumber(value) : value}</p>
        </article>
      `,
    )
    .join("");
}

function renderTable(rows, columns, emptyMessage) {
  if (!rows?.length) {
    return `<div class="empty-state">${emptyMessage}</div>`;
  }
  const header = columns.map((column) => `<th>${column.label}</th>`).join("");
  const body = rows
    .map(
      (row) => `
        <tr>
          ${columns
            .map((column) => `<td>${column.render ? column.render(row[column.key], row) : row[column.key] ?? "—"}</td>`)
            .join("")}
        </tr>
      `,
    )
    .join("");
  return `<table><thead><tr>${header}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderSummary(payload) {
  state.summary = payload;
  renderHeroCards(payload.hero_cards || []);
  generatedAtEl.textContent = formatDate(payload.generated_at);
  subtitleEl.textContent = "Portfolio summary across active lending activity.";
  outstandingTotalEl.textContent = `${payload.outstanding_totals?.loan_count ?? 0} loans`;
  recentCountEl.textContent = `${payload.recent_loans?.length ?? 0} shown`;
  topOutstandingEl.innerHTML = renderTable(
    payload.top_outstanding,
    [
      { key: "name", label: "Loan" },
      { key: "applicant", label: "Applicant" },
      { key: "status", label: "Status" },
      { key: "pending_principal_amount", label: "Outstanding", render: (value) => formatNumber(value) },
      { key: "days_past_due", label: "DPD" },
    ],
    "No outstanding loan rows available.",
  );
  recentLoansEl.innerHTML = renderTable(
    payload.recent_loans,
    [
      { key: "name", label: "Loan" },
      { key: "applicant", label: "Applicant" },
      { key: "loan_product", label: "Product" },
      { key: "status", label: "Status" },
      { key: "posting_date", label: "Posting Date", render: (value) => formatDate(value) },
    ],
    "No recent loan rows available.",
  );
  renderSimpleCards(payload.overview?.cards || {});
}

function renderPayload(payload) {
  renderError("");
  if (!payload) {
    renderError("The dashboard tool returned no structured content.");
    return;
  }
  renderSummary(payload);
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

async function callSummaryTool() {
  state.lastTool = TOOL_SUMMARY;
  renderError("");
  subtitleEl.textContent = "Loading dashboard summary…";
  try {
    const result = await mcpApp.callServerTool({ name: TOOL_SUMMARY, arguments: {} });
    renderPayload(result.structuredContent || null);
  } catch (error) {
    renderError(error instanceof Error ? error.message : "Dashboard tool call failed.");
  }
}

mcpApp.onhostcontextchanged = handleHostContextChanged;
mcpApp.ontoolinput = () => {
  state.lastTool = TOOL_SUMMARY;
};
mcpApp.ontoolresult = (result) => {
  renderPayload(result.structuredContent || null);
};
mcpApp.ontoolcancelled = () => {
  renderError("The dashboard tool call was cancelled.");
};
mcpApp.onerror = (error) => {
  renderError(error instanceof Error ? error.message : "Unexpected dashboard app error.");
};

refreshSummaryBtn.addEventListener("click", callSummaryTool);

mcpApp.connect().then(() => {
  const context = mcpApp.getHostContext();
  if (context) handleHostContextChanged(context);
});
