import { escapeHtml } from '../../utils/dom.js';
import { formatPkr } from '../../utils/money.js';
import {
  fetchPeriodFinancialReport,
  fetchOrderEconomics,
  getOrderEconomicsCsvUrl,
  getPeriodReportCsvUrl,
  fetchAdminMarketingAnalytics,
} from '../../utils/api.js';

export async function renderFinancialReports(container, viewGenerationRef, preferences = null) {
  let periodReport = null;
  let orderEconomics = { orders: [], total_orders: 0, page: 1, limit: 50 };
  let marketingAnalytics = null;
  let expandedOrderIds = new Set();

  // Filters
  let startDate = '';
  let endDate = '';
  let selectedPreset = 'all_time';
  let orderStatusFilter = '';
  let orderSearchQuery = '';
  let orderLimit = 50;
  let orderOffset = 0;

  function setDatePreset(preset) {
    selectedPreset = preset;
    const now = new Date(new Date().toLocaleString('en-US', { timeZone: 'Asia/Karachi' }));
    const pad = n => String(n).padStart(2, '0');
    const toIso = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (preset === 'all_time') {
      startDate = '';
      endDate = '';
    } else if (preset === 'today') {
      const todayStr = toIso(now);
      startDate = todayStr;
      endDate = todayStr;
    } else if (preset === 'this_month') {
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
      const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      startDate = toIso(firstDay);
      endDate = toIso(lastDay);
    } else if (preset === 'last_month') {
      const firstDay = new Date(now.getFullYear(), now.getMonth() - 1, 1);
      const lastDay = new Date(now.getFullYear(), now.getMonth(), 0);
      startDate = toIso(firstDay);
      endDate = toIso(lastDay);
    }
  }

  async function loadData() {
    try {
      container.innerHTML = `
        <div style="padding: 48px 16px; text-align: center; color: rgba(255, 255, 255, 0.45); font-size: 0.8125rem;">
          <div class="spinner" style="margin: 0 auto 14px; width: 28px; height: 28px; border: 2px solid rgba(255,255,255,0.15); border-top-color: #10B981; border-radius: 50%; animation: spin 1s linear infinite;"></div>
          Calculating period financials, cash movements, and unit economics...
        </div>
      `;

      const periodParams = {};
      if (startDate) periodParams.start_date = startDate;
      if (endDate) periodParams.end_date = endDate;
      periodParams.timezone = 'Asia/Karachi';

      const orderParams = { limit: orderLimit, offset: orderOffset };
      if (startDate) orderParams.start_date = startDate;
      if (endDate) orderParams.end_date = endDate;
      if (orderStatusFilter) orderParams.status = orderStatusFilter;
      if (orderSearchQuery) orderParams.search = orderSearchQuery;

      const [pReport, oEcon, mkt] = await Promise.all([
        fetchPeriodFinancialReport(periodParams),
        fetchOrderEconomics(orderParams),
        fetchAdminMarketingAnalytics().catch(() => ({ channels: [] })),
      ]);

      periodReport = pReport;
      orderEconomics = oEcon;
      marketingAnalytics = mkt;
      render();
    } catch (err) {
      container.innerHTML = `
        <div style="padding: 16px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #F87171; font-size: 0.8125rem; margin-bottom: 16px;">
          <strong>Error loading financial reports:</strong> ${escapeHtml(err.message || 'Unknown error')}
        </div>
        <button type="button" id="btn-retry-reports" class="btn btn-secondary" style="padding: 8px 16px; font-size: 0.8125rem;">Retry Loading</button>
      `;
      container.querySelector('#btn-retry-reports')?.addEventListener('click', () => loadData());
    }
  }

  function render() {
    const r = periodReport || {};
    const overhead = r.overhead_expenses || {};

    const csvOrdersUrl = getOrderEconomicsCsvUrl({
      status: orderStatusFilter || undefined,
      search: orderSearchQuery || undefined,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });

    const csvPeriodUrl = getPeriodReportCsvUrl({
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    });

    const isOpResultPos = (r.net_operating_result_minor || 0) >= 0;

    // Desktop Order rows
    const ordersRowsHtml = (orderEconomics.orders || []).map(order => {
      const isExpanded = expandedOrderIds.has(order.order_id);
      const isPositiveMargin = order.estimated_contribution_minor >= 0;
      const statusColorMap = {
        delivered: '#34D399',
        dispatched: '#38BDF8',
        confirmed: '#818CF8',
        placed: '#FBBF24',
        rto: '#F87171',
        cancelled: '#9CA3AF',
      };
      const statusColor = statusColorMap[order.order_status] || '#FFFFFF';

      let linesTableHtml = '';
      if (isExpanded && order.lines && order.lines.length > 0) {
        const lineRows = order.lines.map(line => {
          const isAlphazee = line.ownership_source === 'alphazee_owned';
          return `
            <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.75rem;">
              <td style="padding: 8px 10px; color: #FFFFFF;">
                <strong>${escapeHtml(line.product_title)}</strong>
                ${line.variant_sku ? `<span style="color: rgba(255, 255, 255, 0.4); margin-left: 6px; font-family: monospace;">[${escapeHtml(line.variant_sku)}]</span>` : ''}
                ${(line.variant_color || line.variant_size) ? `<div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5);">${escapeHtml([line.variant_color, line.variant_size].filter(Boolean).join(' / '))}</div>` : ''}
              </td>
              <td style="padding: 8px 10px; text-align: center;">
                <span style="display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.6875rem; font-weight: 500; ${isAlphazee ? 'background: rgba(16, 185, 129, 0.15); color: #34D399;' : 'background: rgba(56, 189, 248, 0.15); color: #38BDF8;'}">
                  ${isAlphazee ? 'AlphaZee Owned' : 'Vendor Consigned'}
                </span>
                ${isAlphazee ? '<div style="font-size: 0.625rem; color: rgba(255, 255, 255, 0.4); margin-top: 2px;">0 vendor liability</div>' : ''}
              </td>
              <td style="padding: 8px 10px; text-align: center; font-variant-numeric: tabular-nums;">${line.quantity}</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace;">${formatPkr(line.unit_cost_minor)}</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace;">${formatPkr(line.unit_price_minor)}</td>
              <td style="padding: 8px 10px; text-align: right; font-family: monospace; font-weight: 600; color: ${line.line_contribution_minor >= 0 ? '#34D399' : '#F87171'};">
                ${formatPkr(line.line_contribution_minor)}
              </td>
            </tr>
          `;
        }).join('');

        linesTableHtml = `
          <tr class="order-detail-row" style="background: rgba(0, 0, 0, 0.4);">
            <td colspan="9" style="padding: 12px 16px;">
              <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600; margin-bottom: 8px; letter-spacing: 0.04em;">
                Line-Item Economics & Supplier Cost Attribution (Order #${escapeHtml(order.order_number)})
              </div>
              <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                  <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); text-transform: uppercase;">
                    <th style="padding: 6px 10px;">Item & Variant</th>
                    <th style="padding: 6px 10px; text-align: center;">Ownership</th>
                    <th style="padding: 6px 10px; text-align: center;">Qty</th>
                    <th style="padding: 6px 10px; text-align: right;">Unit Cost</th>
                    <th style="padding: 6px 10px; text-align: right;">Unit Price</th>
                    <th style="padding: 6px 10px; text-align: right;">Contribution</th>
                  </tr>
                </thead>
                <tbody>
                  ${lineRows}
                </tbody>
              </table>
            </td>
          </tr>
        `;
      }

      return `
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
          <td style="padding: 10px 12px; font-family: monospace; color: #FFFFFF;">
            <strong>#${escapeHtml(order.order_number)}</strong>
            <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); font-family: sans-serif;">${escapeHtml(order.created_at ? order.created_at.slice(0, 10) : '')}</div>
          </td>
          <td style="padding: 10px 12px; color: rgba(255, 255, 255, 0.85);">
            ${escapeHtml(order.customer_name || 'Customer')}
            <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); text-transform: uppercase;">${escapeHtml(order.payment_method)}</div>
          </td>
          <td style="padding: 10px 12px;">
            <span style="font-size: 0.75rem; font-weight: 600; color: ${statusColor};">
              ${escapeHtml(order.order_status.toUpperCase())}
            </span>
          </td>
          <td style="padding: 10px 12px; text-align: right; font-family: monospace; font-weight: 600;">
            ${formatPkr(order.customer_total_minor)}
          </td>
          <td style="padding: 10px 12px; text-align: right; font-family: monospace; color: #F59E0B;">
            ${formatPkr(order.wholesale_cogs_minor)}
          </td>
          <td style="padding: 10px 12px; text-align: right; font-family: monospace; color: #F87171;">
            ${formatPkr(order.total_logistics_cost_minor)}
            ${order.rto_courier_cost_minor > 0 ? `<div style="font-size: 0.625rem; color: #F87171;">RTO: ${formatPkr(order.rto_courier_cost_minor)}</div>` : ''}
          </td>
          <td style="padding: 10px 12px; text-align: right; font-family: monospace; font-size: 0.75rem;">
            <div>Paid: ${formatPkr(order.supplier_payments_minor)}</div>
            ${order.supplier_outstanding_minor > 0 ? `<div style="color: #FBBF24;">Due: ${formatPkr(order.supplier_outstanding_minor)}</div>` : '<div style="color: rgba(255, 255, 255, 0.35);">Settled</div>'}
          </td>
          <td style="padding: 10px 12px; text-align: right; font-family: monospace; font-weight: 700; color: ${isPositiveMargin ? '#34D399' : '#F87171'};">
            ${escapeHtml(order.formatted_contribution)}
          </td>
          <td style="padding: 10px 12px; text-align: center;">
            <button type="button" class="btn-toggle-order-lines rep-icon-btn is-inspect" data-order-id="${escapeHtml(order.order_id)}" data-tooltip="${isExpanded ? 'Hide line details' : 'Inspect line-item economics'}" aria-label="Toggle details for order ${escapeHtml(order.order_number)}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="${isExpanded ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'}"/></svg>
            </button>
          </td>
        </tr>
        ${linesTableHtml}
      `;
    }).join('');

    // Mobile Order Cards (Rule 1: Zero horizontal scroll)
    const ordersCardsHtml = (orderEconomics.orders || []).map(order => {
      const isExpanded = expandedOrderIds.has(order.order_id);
      const isPositiveMargin = order.estimated_contribution_minor >= 0;
      return `
        <div class="rep-order-card">
          <div class="rep-order-card-top">
            <div>
              <span style="font-family: monospace; font-weight: 600; color: #FFFFFF;">#${escapeHtml(order.order_number)}</span>
              <span style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); margin-left: 6px;">${escapeHtml(order.created_at ? order.created_at.slice(0, 10) : '')}</span>
            </div>
            <span style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #34D399;">${escapeHtml(order.order_status)}</span>
          </div>
          <div class="rep-order-card-meta">
            <span>Customer: ${escapeHtml(order.customer_name || 'Customer')}</span>
            <span style="color: #FFFFFF; font-weight: 600;">${formatPkr(order.customer_total_minor)}</span>
          </div>
          <div style="display: flex; justify-content: space-between; font-size: 0.6875rem; color: rgba(255, 255, 255, 0.5); font-variant-numeric: tabular-nums;">
            <span>COGS: ${formatPkr(order.wholesale_cogs_minor)}</span>
            <span>Freight: ${formatPkr(order.total_logistics_cost_minor)}</span>
            <span style="font-weight: 600; color: ${isPositiveMargin ? '#34D399' : '#F87171'};">Margin: ${escapeHtml(order.formatted_contribution)}</span>
          </div>
          <div style="display: flex; justify-content: flex-end; padding-top: 4px;">
            <button type="button" class="btn-toggle-order-lines rep-icon-btn is-inspect" data-order-id="${escapeHtml(order.order_id)}" data-tooltip="${isExpanded ? 'Hide lines' : 'Inspect lines'}" style="width: auto; padding: 4px 10px; font-size: 0.75rem; gap: 4px;">
              <span>${isExpanded ? 'Hide Lines' : 'Inspect Lines'}</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="${isExpanded ? 'M18 15l-6-6-6 6' : 'M6 9l6 6 6-6'}"/></svg>
            </button>
          </div>
          ${isExpanded && order.lines ? `
            <div style="background: rgba(0, 0, 0, 0.3); border-radius: 6px; padding: 10px; margin-top: 6px; display: flex; flex-direction: column; gap: 6px; font-size: 0.75rem;">
              ${order.lines.map(l => `
                <div style="display: flex; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 4px;">
                  <div>
                    <div style="color: #FFFFFF; font-weight: 500;">${escapeHtml(l.product_title)}</div>
                    <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4);">${l.quantity}x @ ${formatPkr(l.unit_price_minor)}</div>
                  </div>
                  <div style="text-align: right; font-family: monospace; font-weight: 600; color: ${l.line_contribution_minor >= 0 ? '#34D399' : '#F87171'};">
                    ${formatPkr(l.line_contribution_minor)}
                  </div>
                </div>
              `).join('')}
            </div>
          ` : ''}
        </div>
      `;
    }).join('');

    // Marketing Rows
    const marketingRowsHtml = ((marketingAnalytics && marketingAnalytics.channels) || []).map(c => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 10px 12px; font-weight: 600; color: #38BDF8;">${escapeHtml(c.utm_source)}</td>
        <td style="padding: 10px 12px; color: rgba(255, 255, 255, 0.7);">${escapeHtml(c.utm_medium)}</td>
        <td style="padding: 10px 12px; color: rgba(255, 255, 255, 0.7);">${escapeHtml(c.utm_campaign)}</td>
        <td style="padding: 10px 12px; font-weight: 600; text-align: center; font-variant-numeric: tabular-nums;">${c.orders_count}</td>
        <td style="padding: 10px 12px; font-weight: 600; color: #34D399; text-align: right; font-family: monospace;">${escapeHtml(c.formatted_revenue)}</td>
        <td style="padding: 10px 12px; color: #F59E0B; text-align: right; font-family: monospace;">${escapeHtml(c.formatted_discount)}</td>
      </tr>
    `).join('');

    // Mobile Marketing Cards
    const marketingCardsHtml = ((marketingAnalytics && marketingAnalytics.channels) || []).map(c => `
      <div style="background: #101318; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 6px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-weight: 600; color: #38BDF8; font-size: 0.8125rem;">${escapeHtml(c.utm_source)}</span>
          <span style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">${escapeHtml(c.utm_medium)} / ${escapeHtml(c.utm_campaign)}</span>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.75rem; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 6px;">
          <span>Orders: ${c.orders_count}</span>
          <span style="font-family: monospace; font-weight: 600; color: #34D399;">${escapeHtml(c.formatted_revenue)}</span>
        </div>
      </div>
    `).join('');

    container.innerHTML = `
      <div class="financial-reports-view">
        
        <!-- Header & Date Period Filter Toolbar -->
        <div class="rep-toolbar">
          <div class="rep-toolbar-top">
            <div>
              <h2 class="rep-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
                Financial Reports & Unit Economics
              </h2>
              <p class="rep-subtitle">
                Authoritative executive P&L, realized cash reconciliation, and line-item supplier attribution.
              </p>
            </div>
            <!-- Rule 2: Compact Semantic Icons for CSV Exports -->
            <div class="rep-actions-group">
              <a id="btn-export-pnl-csv" href="${escapeHtml(csvPeriodUrl)}" download class="rep-icon-btn is-export" data-tooltip="Export P&L statement (CSV)" aria-label="Export P&L statement CSV" title="Export P&L statement (CSV)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2"/><path d="M8 17h2"/><path d="M14 13h2"/><path d="M14 17h2"/></svg>
              </a>
              <a id="btn-export-orders-csv" href="${escapeHtml(csvOrdersUrl)}" download class="rep-icon-btn is-export" data-tooltip="Export per-order unit economics (CSV)" aria-label="Export orders CSV" title="Export orders CSV">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              </a>
            </div>
          </div>

          <!-- Date Filters Row -->
          <div class="rep-toolbar-filters">
            <div class="rep-date-rail">
              <button type="button" class="btn-preset-date rep-preset-pill ${selectedPreset === 'all_time' ? 'active' : ''}" data-preset="all_time">All Time</button>
              <button type="button" class="btn-preset-date rep-preset-pill ${selectedPreset === 'today' ? 'active' : ''}" data-preset="today">Today</button>
              <button type="button" class="btn-preset-date rep-preset-pill ${selectedPreset === 'this_month' ? 'active' : ''}" data-preset="this_month">This Month</button>
              <button type="button" class="btn-preset-date rep-preset-pill ${selectedPreset === 'last_month' ? 'active' : ''}" data-preset="last_month">Last Month</button>
            </div>

            <div class="rep-custom-date">
              <input type="date" id="report-start-date" value="${escapeHtml(startDate)}" class="rep-date-input" aria-label="Report start date" />
              <span style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem;">to</span>
              <input type="date" id="report-end-date" value="${escapeHtml(endDate)}" class="rep-date-input" aria-label="Report end date" />
              <button type="button" id="btn-apply-period" class="rep-icon-btn is-apply" data-tooltip="Apply custom date range" aria-label="Apply custom date range" title="Apply date range">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
            </div>

            <div class="rep-tz-badge">
              <span class="rep-tz-dot"></span>
              <span>Asia/Karachi (UTC+5)</span>
            </div>
          </div>
        </div>

        <!-- Executive KPI 5-Card Grid (High Density Swiss Banking) -->
        <div class="rep-kpis-grid">
          <div class="rep-kpi-card">
            <div class="rep-kpi-label">Delivered Net Revenue</div>
            <div id="kpi-net-revenue" class="rep-kpi-val">
              ${escapeHtml(r.formatted_net_revenue || formatPkr(r.net_revenue_minor || 0))}
            </div>
            <div class="rep-kpi-sub">
              Gross: ${formatPkr(r.gross_revenue_minor || 0)} · Disc: -${formatPkr(r.customer_discounts_minor || 0)}
            </div>
          </div>

          <div class="rep-kpi-card">
            <div class="rep-kpi-label">Net Wholesale COGS</div>
            <div id="kpi-net-cogs" class="rep-kpi-val" style="color: #F59E0B;">
              ${escapeHtml(r.formatted_net_cogs || formatPkr(r.net_cogs_minor || 0))}
            </div>
            <div class="rep-kpi-sub">
              Restock Reversals: -${formatPkr(r.cogs_reversals_minor || 0)}
            </div>
          </div>

          <div class="rep-kpi-card">
            <div class="rep-kpi-label">Unit Contribution</div>
            <div id="kpi-contribution" class="rep-kpi-val" style="color: #38BDF8;">
              ${escapeHtml(r.formatted_contribution_before_overhead || formatPkr(r.contribution_before_overhead_minor || 0))}
            </div>
            <div class="rep-kpi-sub" style="color: #38BDF8;">
              ${(r.contribution_margin_pct ?? 0).toFixed(1)}% margin on net revenue
            </div>
          </div>

          <div class="rep-kpi-card">
            <div class="rep-kpi-label">Freight & Overhead</div>
            <div id="kpi-total-overhead" class="rep-kpi-val" style="color: #F87171;">
              ${formatPkr((r.total_freight_minor || 0) + (r.total_overhead_minor || 0))}
            </div>
            <div class="rep-kpi-sub">
              Freight: ${formatPkr(r.total_freight_minor || 0)} · Op: ${formatPkr(r.total_overhead_minor || 0)}
            </div>
          </div>

          <div class="rep-kpi-card">
            <div class="rep-kpi-label">Net Operating Result</div>
            <div id="kpi-operating-result" class="rep-kpi-val ${isOpResultPos ? 'is-result-pos' : 'is-result-neg'}">
              ${escapeHtml(r.formatted_net_operating_result || formatPkr(r.net_operating_result_minor || 0))}
            </div>
            <div class="rep-kpi-sub" style="color: ${isOpResultPos ? '#34D399' : '#F87171'}; font-weight: 600;">
              ${(r.operating_margin_pct ?? 0).toFixed(1)}% operating margin
            </div>
          </div>
        </div>

        <!-- Section 1 & 2 Split: P&L Statement and Cash Movement -->
        <div class="rep-pnl-split">
          
          <!-- Card 1: P&L Statement -->
          <div class="rep-card">
            <div class="rep-card-header">
              <h3 class="rep-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #34D399;"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>
                Period Income Statement (P&L)
              </h3>
              <span class="rep-card-tag">Delivered Basis</span>
            </div>

            <!-- Revenue Block -->
            <div>
              <div class="rep-sec-title">Revenue</div>
              <div class="rep-line-row">
                <span class="rep-line-label">Gross Delivered Sales</span>
                <span class="rep-line-val">${formatPkr(r.gross_revenue_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Customer Discounts</span>
                <span class="rep-line-val" style="color: #F59E0B;">-${formatPkr(r.customer_discounts_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Customer Shipping Fee</span>
                <span class="rep-line-val">+${formatPkr(r.customer_shipping_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Completed Sales Reversals (Returns)</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr(r.sales_reversals_minor || 0)}</span>
              </div>
              <div class="rep-line-row is-total">
                <span style="color: #34D399;">Net Revenue</span>
                <span class="rep-line-val" style="color: #34D399;">${formatPkr(r.net_revenue_minor || 0)}</span>
              </div>
            </div>

            <!-- COGS Block -->
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 10px;">
              <div class="rep-sec-title">Cost of Goods Sold (COGS)</div>
              <div class="rep-line-row">
                <span class="rep-line-label">Wholesale Product Cost (Snapshot)</span>
                <span class="rep-line-val">${formatPkr(r.gross_cogs_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Sellable Return Restocks (COGS Reversals)</span>
                <span class="rep-line-val" style="color: #34D399;">-${formatPkr(r.cogs_reversals_minor || 0)}</span>
              </div>
              <div class="rep-line-row is-total">
                <span style="color: #F59E0B;">Net Wholesale COGS</span>
                <span class="rep-line-val" style="color: #F59E0B;">${formatPkr(r.net_cogs_minor || 0)}</span>
              </div>
            </div>

            <!-- Contribution Callout Box -->
            <div class="rep-callout-box is-blue">
              <div>
                <div class="rep-callout-title">Contribution Before Overhead</div>
                <div class="rep-callout-sub">Net Revenue less Net COGS</div>
              </div>
              <div style="text-align: right;">
                <div class="rep-callout-val" style="color: #38BDF8;">${formatPkr(r.contribution_before_overhead_minor || 0)}</div>
                <div style="font-size: 0.6875rem; color: #38BDF8; font-weight: 600;">${(r.contribution_margin_pct ?? 0).toFixed(1)}% Margin</div>
              </div>
            </div>

            <!-- Logistics & Overhead Block -->
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span class="rep-sec-title" style="margin: 0;">Evidenced Logistics & Overhead</span>
                <span style="font-size: 0.625rem; color: #60A5FA; background: rgba(96, 165, 250, 0.12); padding: 1px 6px; border-radius: 4px;">AlphaZee-Borne Freight</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Outbound Courier Freight</span>
                <span class="rep-line-val">${formatPkr(r.outbound_freight_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">RTO Transport Freight (100% AlphaZee)</span>
                <span class="rep-line-val" style="color: #F87171;">${formatPkr(r.rto_freight_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Customer Return Freight (100% AlphaZee)</span>
                <span class="rep-line-val" style="color: #F87171;">${formatPkr(r.customer_return_freight_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Packaging & Boxes</span>
                <span class="rep-line-val">${formatPkr(overhead.packaging || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Advertising & Marketing</span>
                <span class="rep-line-val">${formatPkr(overhead.advertising || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Platform & Hosting</span>
                <span class="rep-line-val">${formatPkr(overhead.platform_hosting || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Salaries & Wages</span>
                <span class="rep-line-val">${formatPkr(overhead.salaries || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Office & General Overhead</span>
                <span class="rep-line-val">${formatPkr((overhead.office_supplies || 0) + (overhead.other_overhead || 0))}</span>
              </div>
              <div class="rep-line-row is-total">
                <span style="color: #F87171;">Total Evidenced Logistics & Overhead</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr((r.total_freight_minor || 0) + (r.total_overhead_minor || 0))}</span>
              </div>
            </div>

            <!-- Net Operating Result Box -->
            <div class="rep-callout-box" style="background: rgba(0, 0, 0, 0.4); border-color: rgba(255, 255, 255, 0.1);">
              <div>
                <div class="rep-callout-title" style="font-size: 0.9375rem;">Net Operating Result</div>
                <div class="rep-callout-sub">Contribution less verified transport & overhead</div>
              </div>
              <div style="text-align: right;">
                <div class="rep-callout-val" style="color: ${isOpResultPos ? '#34D399' : '#F87171'}; font-size: 1.25rem;">
                  ${formatPkr(r.net_operating_result_minor || 0)}
                </div>
                <div style="font-size: 0.6875rem; color: ${isOpResultPos ? '#34D399' : '#F87171'}; font-weight: 600;">
                  ${(r.operating_margin_pct ?? 0).toFixed(1)}% Operating Margin
                </div>
              </div>
            </div>
            <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.35); line-height: 1.4;">
              <strong>Disclosure:</strong> Net Operating Result is subject to unrecorded business expenses, courier settlement adjustments, and tax liabilities. Never treat as final audited net profit.
            </div>

          </div>

          <!-- Card 2: Cash Movement & Balance Sheet -->
          <div class="rep-card">
            <div class="rep-card-header">
              <h3 class="rep-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #38BDF8;"><circle cx="12" cy="12" r="10"/><path d="M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8"/><path d="M12 18V6"/></svg>
                Cash Movement & Account Reconciliation
              </h3>
              <span class="rep-card-tag">Realized Cash Flow</span>
            </div>

            <!-- Inflows Block -->
            <div>
              <div class="rep-sec-title">Cash Inflows (Actual Receipts)</div>
              <div class="rep-line-row">
                <span class="rep-line-label">Bank Customer Prepayments Cleared</span>
                <span class="rep-line-val">+${formatPkr(r.bank_prepayments_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Courier COD Cash Remitted into Bank</span>
                <span class="rep-line-val">+${formatPkr(r.courier_cod_remitted_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Supplier Refunds Received</span>
                <span class="rep-line-val">+${formatPkr(r.supplier_refunds_received_minor || 0)}</span>
              </div>
              <div class="rep-line-row is-total">
                <span style="color: #34D399;">Total Cash Inflows</span>
                <span class="rep-line-val" style="color: #34D399;">${formatPkr(r.total_cash_inflows_minor || 0)}</span>
              </div>
            </div>

            <!-- Outflows Block -->
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 10px;">
              <div class="rep-sec-title">Cash Outflows (Disbursements)</div>
              <div class="rep-line-row">
                <span class="rep-line-label">Supplier Payments Disbursed</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr(r.supplier_payments_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Customer Refunds Paid</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr(r.refunds_paid_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Direct Cash & Bank Expenses Paid</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr(r.cash_expenses_paid_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Courier Freight Deductions Settled</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr(r.courier_deductions_minor || 0)}</span>
              </div>
              <div class="rep-line-row is-total">
                <span style="color: #F87171;">Total Cash Outflows</span>
                <span class="rep-line-val" style="color: #F87171;">-${formatPkr(r.total_cash_outflows_minor || 0)}</span>
              </div>
            </div>

            <!-- Net Cash Movement Box -->
            <div class="rep-callout-box" style="background: rgba(0, 0, 0, 0.4); border-color: rgba(255, 255, 255, 0.1);">
              <div>
                <div class="rep-callout-title" style="font-size: 0.9375rem;">Net Cash Movement</div>
                <div class="rep-callout-sub">Realized cash inflow less disbursed outflow</div>
              </div>
              <div style="text-align: right;">
                <div class="rep-callout-val" style="color: ${(r.net_cash_movement_minor || 0) >= 0 ? '#34D399' : '#F87171'}; font-size: 1.25rem;">
                  ${formatPkr(r.net_cash_movement_minor || 0)}
                </div>
              </div>
            </div>

            <!-- Outstanding Receivables & Liabilities Block -->
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 10px;">
              <div class="rep-sec-title">Outstanding Receivables & Liabilities</div>
              <div class="rep-line-row">
                <span class="rep-line-label">Courier-Held COD (Pending Remittance)</span>
                <span class="rep-line-val" style="color: #FBBF24; font-weight: 600;">${formatPkr(r.courier_held_cod_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Outstanding Supplier Liabilities</span>
                <span class="rep-line-val" style="color: #F87171; font-weight: 600;">${formatPkr(r.supplier_liabilities_minor || 0)}</span>
              </div>
              <div class="rep-line-row">
                <span class="rep-line-label">Customer Refund Liabilities Payable</span>
                <span class="rep-line-val" style="color: #F87171; font-weight: 600;">${formatPkr(r.refund_liabilities_minor || 0)}</span>
              </div>
            </div>

          </div>

        </div>

        <!-- Section 3: Per-Order Economics & Margin Inspection -->
        <div class="rep-card">
          <div class="rep-orders-toolbar">
            <div>
              <h3 class="rep-card-title">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #10B981;"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
                Per-Order Economics & Unit Margins
              </h3>
              <p class="rep-subtitle" style="margin-top: 2px;">
                Wholesale cost, outbound freight, RTO penalties, and stock ownership source per order.
              </p>
            </div>

            <!-- Order Table Filter Controls -->
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <select id="report-order-status-filter" class="rep-status-select" aria-label="Filter by order status">
                <option value="" ${orderStatusFilter === '' ? 'selected' : ''}>All Order Statuses</option>
                <option value="delivered" ${orderStatusFilter === 'delivered' ? 'selected' : ''}>Delivered</option>
                <option value="dispatched" ${orderStatusFilter === 'dispatched' ? 'selected' : ''}>Dispatched</option>
                <option value="confirmed" ${orderStatusFilter === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                <option value="placed" ${orderStatusFilter === 'placed' ? 'selected' : ''}>Placed</option>
                <option value="rto" ${orderStatusFilter === 'rto' ? 'selected' : ''}>RTO</option>
                <option value="cancelled" ${orderStatusFilter === 'cancelled' ? 'selected' : ''}>Cancelled</option>
              </select>

              <input type="text" id="report-order-search" class="rep-search-input" placeholder="Search order # or customer..." value="${escapeHtml(orderSearchQuery)}" aria-label="Search orders" />

              <button type="button" id="btn-filter-orders" class="rep-icon-btn is-apply" data-tooltip="Filter orders" aria-label="Filter orders" title="Filter orders">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
              </button>
            </div>
          </div>

          <!-- Desktop Order Economics Table (Rule 1: Zero horizontal scroll) -->
          <div class="rep-table-wrap rep-table-desktop">
            <table class="admin-table">
              <thead>
                <tr>
                  <th style="width: 130px;">Order #</th>
                  <th>Customer</th>
                  <th style="width: 100px;">Status</th>
                  <th style="text-align: right; width: 110px;">Total</th>
                  <th style="text-align: right; width: 100px;">COGS</th>
                  <th style="text-align: right; width: 100px;">Logistics</th>
                  <th style="text-align: right; width: 110px;">Payables</th>
                  <th style="text-align: right; width: 110px;">Contribution</th>
                  <th style="text-align: center; width: 60px;">Lines</th>
                </tr>
              </thead>
              <tbody>
                ${ordersRowsHtml.length ? ordersRowsHtml : '<tr><td colspan="9" style="padding: 36px 12px; text-align: center; color: rgba(255,255,255,0.4);">No orders recorded for this period matching the selected criteria.</td></tr>'}
              </tbody>
            </table>
          </div>

          <!-- Mobile Order Cards (Rule 1: Zero horizontal scroll) -->
          <div class="rep-order-cards">
            ${ordersCardsHtml.length ? ordersCardsHtml : '<div style="padding: 24px 12px; text-align: center; color: rgba(255,255,255,0.4);">No orders recorded matching criteria.</div>'}
          </div>

          <!-- Total count and pagination -->
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.06);">
            <div>Showing ${(orderEconomics.orders || []).length} of ${orderEconomics.total_orders || 0} orders</div>
            ${orderEconomics.total_orders > orderLimit ? `
              <div style="display: flex; gap: 6px;">
                <button type="button" id="btn-orders-prev" ${orderOffset === 0 ? 'disabled' : ''} class="rep-icon-btn" data-tooltip="Previous page" style="width: auto; padding: 4px 10px; font-size: 0.75rem;">Prev</button>
                <button type="button" id="btn-orders-next" ${orderOffset + orderLimit >= orderEconomics.total_orders ? 'disabled' : ''} class="rep-icon-btn" data-tooltip="Next page" style="width: auto; padding: 4px 10px; font-size: 0.75rem;">Next</button>
              </div>
            ` : ''}
          </div>

        </div>

        <!-- Section 4: Marketing Attribution & Campaign Conversion (UTM) -->
        <div class="rep-card">
          <div class="rep-card-header">
            <h3 class="rep-card-title">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: #38BDF8;"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>
              Marketing Attribution & Campaign Conversion (UTM)
            </h3>
            <span class="rep-card-tag">${((marketingAnalytics && marketingAnalytics.channels) || []).length} Channels</span>
          </div>

          <!-- Desktop UTM Table -->
          <div class="rep-table-wrap rep-table-desktop">
            <table class="admin-table">
              <thead>
                <tr>
                  <th>UTM Source</th>
                  <th>Medium</th>
                  <th>Campaign</th>
                  <th style="text-align: center; width: 90px;">Orders</th>
                  <th style="text-align: right; width: 130px;">Delivered Sales</th>
                  <th style="text-align: right; width: 120px;">Discounts</th>
                </tr>
              </thead>
              <tbody>
                ${marketingRowsHtml.length ? marketingRowsHtml : '<tr><td colspan="6" style="padding: 24px 12px; text-align: center; color: rgba(255,255,255,0.4);">No UTM attribution data recorded for this period.</td></tr>'}
              </tbody>
            </table>
          </div>

          <!-- Mobile UTM Cards -->
          <div class="rep-order-cards">
            ${marketingCardsHtml.length ? marketingCardsHtml : '<div style="padding: 16px; text-align: center; color: rgba(255,255,255,0.4);">No UTM attribution data recorded.</div>'}
          </div>
        </div>

      </div>
    `;

    // Event Listeners: Date Presets
    container.querySelectorAll('.btn-preset-date').forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = btn.getAttribute('data-preset');
        setDatePreset(preset);
        loadData();
      });
    });

    // Custom Date Apply
    container.querySelector('#btn-apply-period')?.addEventListener('click', () => {
      const sInput = container.querySelector('#report-start-date');
      const eInput = container.querySelector('#report-end-date');
      startDate = sInput?.value || '';
      endDate = eInput?.value || '';
      selectedPreset = 'custom';
      loadData();
    });

    // Order Filters
    const orderStatusSelect = container.querySelector('#report-order-status-filter');
    if (orderStatusSelect) {
      orderStatusSelect.addEventListener('change', () => {
        orderStatusFilter = orderStatusSelect.value || '';
        orderOffset = 0;
        loadData();
      });
    }

    let searchTimer = null;
    const orderSearchInput = container.querySelector('#report-order-search');
    if (orderSearchInput) {
      orderSearchInput.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
          orderSearchQuery = orderSearchInput.value.trim();
          orderOffset = 0;
          loadData();
        }, 300);
      });
      orderSearchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          clearTimeout(searchTimer);
          orderSearchQuery = orderSearchInput.value.trim();
          orderOffset = 0;
          loadData();
        }
      });
    }

    container.querySelector('#btn-filter-orders')?.addEventListener('click', () => {
      const sSelect = container.querySelector('#report-order-status-filter');
      const qInput = container.querySelector('#report-order-search');
      orderStatusFilter = sSelect?.value || '';
      orderSearchQuery = qInput?.value || '';
      orderOffset = 0;
      loadData();
    });

    // Order Pagination
    container.querySelector('#btn-orders-prev')?.addEventListener('click', () => {
      if (orderOffset >= orderLimit) {
        orderOffset -= orderLimit;
        loadData();
      }
    });

    container.querySelector('#btn-orders-next')?.addEventListener('click', () => {
      if (orderOffset + orderLimit < orderEconomics.total_orders) {
        orderOffset += orderLimit;
        loadData();
      }
    });

    // Toggle Order Lines
    container.querySelectorAll('.btn-toggle-order-lines').forEach(btn => {
      btn.addEventListener('click', () => {
        const orderId = btn.getAttribute('data-order-id');
        if (expandedOrderIds.has(orderId)) {
          expandedOrderIds.delete(orderId);
        } else {
          expandedOrderIds.add(orderId);
        }
        render();
      });
    });
  }

  // Initial load
  setDatePreset(preferences?.default_date_range || 'all_time');
  await loadData();
}
