from __future__ import annotations


def render_loan_dashboard_page() -> str:
    return """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Lending MCP Dashboard</title>
    <style>
      :root {
        color-scheme: light dark;
        --bg: #0b1020;
        --panel: #131a2f;
        --panel-border: #27314e;
        --muted: #93a0bd;
        --text: #eff4ff;
        --accent: #78d6ff;
        --accent-2: #6ee7b7;
        --danger: #fb7185;
        --warning: #fbbf24;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: Inter, Segoe UI, Arial, sans-serif;
        background: linear-gradient(180deg, #0b1020 0%, #10182d 100%);
        color: var(--text);
      }
      .wrap {
        max-width: 1240px;
        margin: 0 auto;
        padding: 32px 20px 40px;
      }
      .header {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: end;
        margin-bottom: 24px;
      }
      .title {
        margin: 0;
        font-size: 32px;
        font-weight: 700;
      }
      .subtitle {
        margin-top: 8px;
        color: var(--muted);
        font-size: 14px;
      }
      .diag {
        margin-top: 12px;
        padding: 10px 12px;
        border: 1px dashed rgba(147, 160, 189, 0.35);
        border-radius: 12px;
        font-size: 12px;
        color: var(--muted);
        background: rgba(10, 16, 31, 0.35);
      }
      .diag strong {
        color: var(--text);
      }
      .refresh {
        border: 1px solid var(--panel-border);
        background: #16203a;
        color: var(--text);
        border-radius: 10px;
        padding: 10px 14px;
        cursor: pointer;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 16px;
        margin-bottom: 24px;
      }
      .card, .panel {
        background: rgba(19, 26, 47, 0.92);
        border: 1px solid var(--panel-border);
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
      }
      .card { padding: 18px; min-height: 122px; }
      .card-label {
        color: var(--muted);
        font-size: 13px;
        margin-bottom: 10px;
      }
      .card-value {
        font-size: 28px;
        font-weight: 700;
        line-height: 1.1;
      }
      .card-tone-accent .card-value { color: var(--accent); }
      .card-tone-success .card-value { color: var(--accent-2); }
      .card-tone-warning .card-value { color: var(--warning); }
      .two-col {
        display: grid;
        grid-template-columns: 1.2fr 1fr;
        gap: 16px;
        margin-bottom: 16px;
      }
      .panel { padding: 18px; }
      .panel h2 {
        margin: 0 0 14px;
        font-size: 18px;
      }
      table {
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
      }
      th, td {
        text-align: left;
        padding: 10px 8px;
        border-bottom: 1px solid rgba(147, 160, 189, 0.15);
      }
      th { color: var(--muted); font-weight: 600; }
      .actions {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }
      .action {
        border: 1px solid var(--panel-border);
        border-radius: 12px;
        padding: 14px;
        background: rgba(10, 16, 31, 0.45);
      }
      .action-tool {
        color: var(--accent);
        font-size: 12px;
        margin-top: 6px;
      }
      .meta, .empty, .error {
        color: var(--muted);
        font-size: 13px;
      }
      .error { color: #fecaca; }
      @media (max-width: 1100px) {
        .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .two-col, .actions { grid-template-columns: 1fr; }
      }
      @media (max-width: 700px) {
        .header { flex-direction: column; align-items: start; }
        .grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="header">
        <div>
          <h1 class="title">Loan Dashboard</h1>
          <div class="subtitle" id="generated-at">Loading summary...</div>
          <div class="diag" id="diag">Booting widget...</div>
        </div>
        <button class="refresh" id="refresh-btn" type="button">Refresh</button>
      </div>

      <section class="grid" id="hero-cards"></section>

      <section class="two-col">
        <div class="panel">
          <h2>Top Outstanding Loans</h2>
          <div id="outstanding-meta" class="meta"></div>
          <table>
            <thead>
              <tr>
                <th>Loan</th>
                <th>Applicant</th>
                <th>Status</th>
                <th>Principal Outstanding</th>
                <th>DPD</th>
              </tr>
            </thead>
            <tbody id="top-outstanding-body"></tbody>
          </table>
        </div>
        <div class="panel">
          <h2>Recent Loans</h2>
          <table>
            <thead>
              <tr>
                <th>Loan</th>
                <th>Applicant</th>
                <th>Product</th>
                <th>Status</th>
                <th>Disbursed</th>
              </tr>
            </thead>
            <tbody id="recent-loans-body"></tbody>
          </table>
        </div>
      </section>

      <section class="panel">
        <h2>Suggested MCP Tools</h2>
        <div class="actions" id="actions"></div>
      </section>
    </div>

    <script>
      const bridge = window.mcpApp || null;
      const fmtCurrency = new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 2 });
      const fmtNumber = new Intl.NumberFormat();
      const state = {
        pending: new Map(),
        nextId: 1,
        payload: null,
        hostContext: null,
      };

      function formatMoney(value) {
        return fmtCurrency.format(Number(value || 0));
      }

      function formatCount(value) {
        return fmtNumber.format(Number(value || 0));
      }

      function setDiag(message) {
        const diag = document.getElementById("diag");
        if (diag) {
          diag.innerHTML = `<strong>Widget status:</strong> ${message}`;
        }
      }

      function renderRows(rows, tbodyId, columns, emptyMessage) {
        const tbody = document.getElementById(tbodyId);
        tbody.innerHTML = "";
        if (!rows || !rows.length) {
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = columns;
          td.className = "empty";
          td.textContent = emptyMessage;
          tr.appendChild(td);
          tbody.appendChild(tr);
          return;
        }
        rows.forEach((row) => tbody.appendChild(row));
      }

      function normalizePayload(payload) {
        if (!payload) {
          return null;
        }
        if (payload.overview) {
          return payload;
        }
        return {
          generated_at: payload.generated_at || new Date().toISOString(),
          overview: payload,
          hero_cards: [
            { key: "active_loans", label: "Active Loans", value: String(payload.cards?.active_loans ?? 0), tone: "accent" },
            { key: "open_loan_applications", label: "Open Applications", value: String(payload.cards?.open_loan_applications ?? 0), tone: "default" },
            { key: "closed_loans", label: "Closed Loans", value: String(payload.cards?.closed_loans ?? 0), tone: "default" },
            { key: "total_disbursed", label: "Total Disbursed", value: Number(payload.cards?.total_disbursed ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), tone: "success" },
            { key: "total_repayment", label: "Total Repayment", value: Number(payload.cards?.total_repayment ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), tone: "warning" }
          ],
          recent_loans: [],
          top_outstanding: [],
          outstanding_totals: {
            pending_principal_amount: 0,
            total_amount_paid: 0,
            loan_count: 0
          },
          actions: [
            { label: "Loan Dashboard Summary", tool: "dashboard_loan_summary", description: "Open the dashboard-focused portfolio summary." },
            { label: "Portfolio Overview", tool: "dashboard_overview", description: "Fetch the canonical KPI snapshot." }
          ]
        };
      }

      function sendRequest(method, params = {}) {
        const id = state.nextId++;
        window.parent.postMessage({ jsonrpc: "2.0", id, method, params }, "*");
        return new Promise((resolve, reject) => {
          state.pending.set(id, { resolve, reject });
          window.setTimeout(() => {
            if (state.pending.has(id)) {
              state.pending.delete(id);
              reject(new Error(`${method} timed out`));
            }
          }, 15000);
        });
      }

      function sendNotification(method, params = {}) {
        window.parent.postMessage({ jsonrpc: "2.0", method, params }, "*");
      }

      function announceInitialized(source) {
        sendNotification("ui/notifications/initialized", {});
        setDiag(`initialized via ${source}`);
      }

      function announceSizeChanged() {
        const height = Math.max(
          document.body.scrollHeight,
          document.documentElement.scrollHeight,
          document.body.offsetHeight,
          document.documentElement.offsetHeight
        );
        sendNotification("ui/notifications/size-changed", { width: null, height });
      }

      function applyHostStyles(hostContext) {
        if (!hostContext?.styles?.variables) {
          return;
        }
        Object.entries(hostContext.styles.variables).forEach(([key, value]) => {
          if (typeof value === "string" && value) {
            document.documentElement.style.setProperty(key, value);
          }
        });
      }

      function renderPayload(rawPayload) {
        const generatedAt = document.getElementById("generated-at");
        const heroCards = document.getElementById("hero-cards");
        const actions = document.getElementById("actions");
        const outstandingMeta = document.getElementById("outstanding-meta");
        heroCards.innerHTML = "";
        actions.innerHTML = "";
        const payload = normalizePayload(rawPayload);
        state.payload = payload;

        if (!payload) {
          generatedAt.textContent = "No dashboard payload received";
          setDiag("initialized, but no structured payload arrived");
          return;
        }

        try {
          generatedAt.textContent = `Generated ${payload.generated_at}`;
          setDiag("structured payload rendered");

          payload.hero_cards.forEach((card) => {
            const div = document.createElement("section");
            div.className = `card card-tone-${card.tone}`;
            div.innerHTML = `<div class="card-label">${card.label}</div><div class="card-value">${card.value}</div>`;
            heroCards.appendChild(div);
          });

          outstandingMeta.textContent = `Total principal outstanding: ${formatMoney(payload.outstanding_totals.pending_principal_amount || 0)}`;

          renderRows(
            payload.top_outstanding.map((row) => {
              const tr = document.createElement("tr");
              tr.innerHTML = `
                <td>${row.loan || ""}</td>
                <td>${row.applicant || ""}</td>
                <td>${row.status || ""}</td>
                <td>${formatMoney(row.pending_principal_amount)}</td>
                <td>${formatCount(row.days_past_due)}</td>
              `;
              return tr;
            }),
            "top-outstanding-body",
            5,
            "No outstanding data available."
          );

          renderRows(
            payload.recent_loans.map((row) => {
              const tr = document.createElement("tr");
              tr.innerHTML = `
                <td>${row.name || ""}</td>
                <td>${row.applicant || ""}</td>
                <td>${row.loan_product || ""}</td>
                <td>${row.status || ""}</td>
                <td>${formatMoney(row.disbursed_amount)}</td>
              `;
              return tr;
            }),
            "recent-loans-body",
            5,
            "No recent loans available."
          );

          payload.actions.forEach((action) => {
            const div = document.createElement("div");
            div.className = "action";
            div.innerHTML = `
              <div><strong>${action.label}</strong></div>
              <div class="meta">${action.description}</div>
              <div class="action-tool">${action.tool}</div>
            `;
            actions.appendChild(div);
          });

          announceSizeChanged();
        } catch (error) {
          generatedAt.textContent = "Dashboard load failed";
          heroCards.innerHTML = `<div class="error">${error.message}</div>`;
          setDiag(`render error: ${error.message}`);
        }
      }

      async function refreshFromTool() {
        const generatedAt = document.getElementById("generated-at");
        generatedAt.textContent = "Refreshing dashboard...";
        setDiag("refresh requested");
        try {
          if (bridge && typeof bridge.callTool === "function") {
            const result = await bridge.callTool("dashboard_loan_summary_refresh", {});
            renderPayload(result?.structuredContent || result?.toolResult?.structuredContent || null);
            return;
          }

          const result = await sendRequest("tools/call", {
            name: "dashboard_loan_summary_refresh",
            arguments: {}
          });
          renderPayload(result?.structuredContent || null);
        } catch (error) {
          generatedAt.textContent = `Refresh failed: ${error.message}`;
          setDiag(`refresh failed: ${error.message}`);
        }
      }

      window.addEventListener("message", (event) => {
        const message = event.data;
        if (!message || message.jsonrpc !== "2.0") {
          return;
        }
        if (typeof message.id !== "undefined" && state.pending.has(message.id)) {
          const pending = state.pending.get(message.id);
          state.pending.delete(message.id);
          if (message.error) {
            pending.reject(new Error(message.error.message || "Request failed"));
          } else {
            pending.resolve(message.result);
          }
          return;
        }

        if (message.method === "ui/notifications/tool-result") {
          setDiag("received raw tool-result notification");
          renderPayload(message.params?.structuredContent || null);
          return;
        }

        if (message.method === "ui/notifications/tool-cancelled") {
          document.getElementById("generated-at").textContent = "Dashboard request cancelled";
          setDiag("tool call cancelled by host");
          return;
        }

        if (message.method === "ui/notifications/host-context-changed") {
          state.hostContext = message.params || state.hostContext;
          applyHostStyles(state.hostContext);
          setDiag("host context updated");
          return;
        }

        if (message.method === "ui/resource-teardown" && typeof message.id !== "undefined") {
          window.parent.postMessage({ jsonrpc: "2.0", id: message.id, result: {} }, "*");
        }
      });

      document.getElementById("refresh-btn").addEventListener("click", refreshFromTool);

      function startWithMcpApp() {
        document.getElementById("generated-at").textContent = "Loading dashboard...";
        setDiag("mcpApp bridge detected");

        try {
          state.hostContext = bridge.hostContext || null;
          applyHostStyles(state.hostContext);
          announceInitialized("mcpApp bridge");

          const toolResult = bridge.toolResult || null;
          if (toolResult?.structuredContent) {
            renderPayload(toolResult.structuredContent);
          } else if (toolResult) {
            renderPayload(toolResult);
          } else {
            document.getElementById("generated-at").textContent = "Waiting for dashboard data...";
            setDiag("initialized; waiting for bridge toolResult");
          }

          window.addEventListener("mcp:tool-result", (event) => {
            const detail = event.detail || {};
            setDiag("received mcp:tool-result event");
            renderPayload(detail.structuredContent || detail.toolResult?.structuredContent || null);
          });

          window.addEventListener("mcp:context-change", (event) => {
            const detail = event.detail || {};
            state.hostContext = detail.hostContext || detail || state.hostContext;
            applyHostStyles(state.hostContext);
            setDiag("received mcp:context-change event");
          });

          window.addEventListener("mcp:tool-cancelled", () => {
            document.getElementById("generated-at").textContent = "Dashboard request cancelled";
            setDiag("received mcp:tool-cancelled event");
          });

          window.addEventListener("mcp:teardown", () => {
            document.getElementById("generated-at").textContent = "Dashboard torn down";
            setDiag("received mcp:teardown event");
          });
        } catch (error) {
          document.getElementById("generated-at").textContent = `mcpApp render failed: ${error.message}`;
          setDiag(`mcpApp bridge failed: ${error.message}`);
        }
      }

      async function startWithRawBridge() {
        document.getElementById("generated-at").textContent = "Initializing dashboard...";
        setDiag("using raw postMessage bridge");
        try {
          const init = await sendRequest("ui/initialize", {
            appCapabilities: {
              availableDisplayModes: ["inline", "fullscreen"]
            }
          });
          state.hostContext = init?.hostContext || null;
          applyHostStyles(state.hostContext);
          announceInitialized("raw bridge");
          document.getElementById("generated-at").textContent = "Waiting for dashboard data...";
          setDiag("raw bridge initialized; waiting for tool result");
        } catch (error) {
          document.getElementById("generated-at").textContent = `Initialization failed: ${error.message}`;
          setDiag(`raw bridge initialization failed: ${error.message}`);
        }
      }

      if (bridge) {
        startWithMcpApp();
      } else {
        startWithRawBridge();
      }
    </script>
  </body>
</html>
"""
