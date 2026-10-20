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
    // Use UTC/local date calculations for presets
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
        <div style="padding: 32px 16px; text-align: center; color: rgba(255, 255, 255, 0.6); font-size: 0.875rem;">
          <div class="spinner" style="margin: 0 auto 12px; width: 24px; height: 24px; border: 2px solid rgba(255,255,255,0.2); border-top-color: #38BDF8; border-radius: 50%; animation: spin 1s linear infinite;"></div>
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
        <div style="padding: 16px; background: rgba(220, 38, 38, 0.15); border: 1px solid rgba(220, 38, 38, 0.3); border-radius: 8px; color: #FCA5A5; font-size: 0.875rem; margin-bottom: 16px;">
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

    // Orders rows
    const ordersRowsHtml = (orderEconomics.orders || []).map(order => {
      const isExpanded = expandedOrderIds.has(order.order_id);
      const isPositiveMargin = order.estimated_contribution_minor >= 0;
      const statusColorMap = {
        delivered: '#4ADE80',
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
              <td style="padding: 6px 8px; color: #FFFFFF;">
                <strong>${escapeHtml(line.product_title)}</strong>
                ${line.variant_sku ? `<span style="color: rgba(255, 255, 255, 0.4); margin-left: 6px;">[${escapeHtml(line.variant_sku)}]</span>` : ''}
                ${(line.variant_color || line.variant_size) ? `<div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5);">${escapeHtml([line.variant_color, line.variant_size].filter(Boolean).join(' / '))}</div>` : ''}
              </td>
              <td style="padding: 6px 8px; text-align: center;">
                <span style="display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 0.6875rem; font-weight: 600; ${isAlphazee ? 'background: rgba(34, 197, 94, 0.2); color: #86EFAC;' : 'background: rgba(59, 130, 246, 0.2); color: #93C5FD;'}">
                  ${isAlphazee ? 'AlphaZee Owned' : 'Vendor Consigned'}
                </span>
                ${isAlphazee ? '<div style="font-size: 0.65rem; color: rgba(255, 255, 255, 0.4); margin-top: 2px;">0 vendor liability</div>' : ''}
              </td>
              <td style="padding: 6px 8px; text-align: center;">${line.quantity}</td>
              <td style="padding: 6px 8px; text-align: right; font-family: monospace;">${formatPkr(line.unit_cost_minor)}</td>
              <td style="padding: 6px 8px; text-align: right; font-family: monospace;">${formatPkr(line.unit_price_minor)}</td>
              <td style="padding: 6px 8px; text-align: right; font-family: monospace; font-weight: 700; color: ${line.line_contribution_minor >= 0 ? '#4ADE80' : '#F87171'};">
                ${formatPkr(line.line_contribution_minor)}
              </td>
            </tr>
          `;
        }).join('');

        linesTableHtml = `
          <tr class="order-detail-row" style="background: rgba(0, 0, 0, 0.35);">
            <td colspan="10" style="padding: 12px 16px;">
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.6); text-transform: uppercase; font-weight: 700; margin-bottom: 8px; letter-spacing: 0.5px;">
                Line-Item Economics & Supplier Cost Attribution (Order #${escapeHtml(order.order_number)})
              </div>
              <table style="width: 100%; border-collapse: collapse; text-align: left;">
                <thead>
                  <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); text-transform: uppercase;">
                    <th style="padding: 6px 8px;">Item & Variant</th>
                    <th style="padding: 6px 8px; text-align: center;">Ownership</th>
                    <th style="padding: 6px 8px; text-align: center;">Qty</th>
                    <th style="padding: 6px 8px; text-align: right;">Unit Cost</th>
                    <th style="padding: 6px 8px; text-align: right;">Unit Price</th>
                    <th style="padding: 6px 8px; text-align: right;">Contribution</th>
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
          <td style="padding: 10px 8px; font-family: monospace; color: #FFFFFF;">
            <strong>#${escapeHtml(order.order_number)}</strong>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); font-family: sans-serif;">${escapeHtml(order.created_at ? order.created_at.slice(0, 10) : '')}</div>
          </td>
          <td style="padding: 10px 8px; color: rgba(255, 255, 255, 0.85);">
            ${escapeHtml(order.customer_name || 'Customer')}
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); text-transform: uppercase;">${escapeHtml(order.payment_method)}</div>
          </td>
          <td style="padding: 10px 8px;">
            <span style="font-size: 0.75rem; font-weight: 700; color: ${statusColor};">
              ${escapeHtml(order.order_status.toUpperCase())}
            </span>
          </td>
          <td style="padding: 10px 8px; text-align: right; font-family: monospace; font-weight: 600;">
            ${formatPkr(order.customer_total_minor)}
          </td>
          <td style="padding: 10px 8px; text-align: right; font-family: monospace; color: #F59E0B;">
            ${formatPkr(order.wholesale_cogs_minor)}
          </td>
          <td style="padding: 10px 8px; text-align: right; font-family: monospace; color: #F87171;">
            ${formatPkr(order.total_logistics_cost_minor)}
            ${order.rto_courier_cost_minor > 0 ? `<div style="font-size: 0.65rem; color: #F87171;">RTO: ${formatPkr(order.rto_courier_cost_minor)}</div>` : ''}
          </td>
          <td style="padding: 10px 8px; text-align: right; font-family: monospace; font-size: 0.75rem;">
            <div>Paid: ${formatPkr(order.supplier_payments_minor)}</div>
            ${order.supplier_outstanding_minor > 0 ? `<div style="color: #FBBF24;">Due: ${formatPkr(order.supplier_outstanding_minor)}</div>` : '<div style="color: rgba(255, 255, 255, 0.35);">Settled</div>'}
          </td>
          <td style="padding: 10px 8px; text-align: right; font-family: monospace; font-weight: 800; color: ${isPositiveMargin ? '#4ADE80' : '#F87171'};">
            ${escapeHtml(order.formatted_contribution)}
          </td>
          <td style="padding: 10px 8px; text-align: center;">
            <button type="button" class="btn-toggle-order-lines" data-order-id="${escapeHtml(order.order_id)}" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.15); color: rgba(255, 255, 255, 0.85); padding: 3px 8px; border-radius: 4px; font-size: 0.72rem; cursor: pointer;">
              ${isExpanded ? 'Hide' : 'Inspect'}
            </button>
          </td>
        </tr>
        ${linesTableHtml}
      `;
    }).join('');

    // Marketing Rows
    const marketingRowsHtml = ((marketingAnalytics && marketingAnalytics.channels) || []).map(c => `
      <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06); font-size: 0.8125rem;">
        <td style="padding: 8px; font-weight: 700; color: #38BDF8;">${escapeHtml(c.utm_source)}</td>
        <td style="padding: 8px;">${escapeHtml(c.utm_medium)}</td>
        <td style="padding: 8px;">${escapeHtml(c.utm_campaign)}</td>
        <td style="padding: 8px; font-weight: 600; text-align: center;">${c.orders_count}</td>
        <td style="padding: 8px; font-weight: 700; color: #4ADE80; text-align: right;">${escapeHtml(c.formatted_revenue)}</td>
        <td style="padding: 8px; color: #F59E0B; text-align: right;">${escapeHtml(c.formatted_discount)}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <div class="financial-reports-view" style="display: flex; flex-direction: column; gap: 24px;">
        
        <!-- Header & Date Period Filter Toolbar -->
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 16px; display: flex; flex-direction: column; gap: 12px;">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
              <h3 style="font-size: 1.125rem; font-weight: 700; color: #FFFFFF; margin: 0 0 4px 0;">Executive P&L, Cash Reconciliation & Unit Economics</h3>
              <div style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">
                Authoritative financial reporting with Karachi timezone day boundaries (UTC+5) and complete formula-safe exports.
              </div>
            </div>
            <div style="display: flex; gap: 8px; flex-wrap: wrap;">
              <a id="btn-export-pnl-csv" href="${escapeHtml(csvPeriodUrl)}" download class="btn btn-secondary" style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 0.78125rem; text-decoration: none; border-radius: 6px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); color: #FFF;">
                📊 Export P&L Statement (CSV)
              </a>
              <a id="btn-export-orders-csv" href="${escapeHtml(csvOrdersUrl)}" download class="btn btn-secondary" style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; font-size: 0.78125rem; text-decoration: none; border-radius: 6px; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.15); color: #FFF;">
                📦 Export Orders CSV
              </a>
            </div>
          </div>

          <!-- Date Filters Row -->
          <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding-top: 10px; border-top: 1px solid rgba(255, 255, 255, 0.06);">
            <div style="display: flex; gap: 6px;">
              <button type="button" class="btn-preset-date ${selectedPreset === 'all_time' ? 'active' : ''}" data-preset="all_time" style="padding: 5px 10px; font-size: 0.75rem; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.15); background: ${selectedPreset === 'all_time' ? 'rgba(20, 92, 68, 0.6)' : 'transparent'}; color: #FFF; cursor: pointer;">All Time</button>
              <button type="button" class="btn-preset-date ${selectedPreset === 'today' ? 'active' : ''}" data-preset="today" style="padding: 5px 10px; font-size: 0.75rem; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.15); background: ${selectedPreset === 'today' ? 'rgba(20, 92, 68, 0.6)' : 'transparent'}; color: #FFF; cursor: pointer;">Today</button>
              <button type="button" class="btn-preset-date ${selectedPreset === 'this_month' ? 'active' : ''}" data-preset="this_month" style="padding: 5px 10px; font-size: 0.75rem; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.15); background: ${selectedPreset === 'this_month' ? 'rgba(20, 92, 68, 0.6)' : 'transparent'}; color: #FFF; cursor: pointer;">This Month</button>
              <button type="button" class="btn-preset-date ${selectedPreset === 'last_month' ? 'active' : ''}" data-preset="last_month" style="padding: 5px 10px; font-size: 0.75rem; border-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.15); background: ${selectedPreset === 'last_month' ? 'rgba(20, 92, 68, 0.6)' : 'transparent'}; color: #FFF; cursor: pointer;">Last Month</button>
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5);">Custom:</span>
              <input type="date" id="report-start-date" value="${escapeHtml(startDate)}" style="background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem;" />
              <span style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem;">to</span>
              <input type="date" id="report-end-date" value="${escapeHtml(endDate)}" style="background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem;" />
              <button type="button" id="btn-apply-period" style="background: #166534; border: 1px solid #22C55E; color: #FFF; border-radius: 4px; padding: 4px 12px; font-size: 0.75rem; font-weight: 600; cursor: pointer;">Apply</button>
            </div>

            <div style="font-size: 0.72rem; color: #38BDF8; margin-left: auto; display: flex; align-items: center; gap: 4px;">
              <span>🌐</span> Reporting Timezone: <strong>Asia/Karachi (UTC+5)</strong>
            </div>
          </div>
        </div>

        <!-- KPI Summary Cards (5-Column) -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          
          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600;">Delivered Net Revenue</div>
            <div id="kpi-net-revenue" style="font-size: 1.4rem; font-weight: 800; color: #4ADE80; margin-top: 4px;">
              ${escapeHtml(r.formatted_net_revenue || formatPkr(r.net_revenue_minor || 0))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">
              Gross: ${formatPkr(r.gross_revenue_minor || 0)} · Disc: -${formatPkr(r.customer_discounts_minor || 0)}
            </div>
          </div>

          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600;">Net Wholesale COGS</div>
            <div id="kpi-net-cogs" style="font-size: 1.4rem; font-weight: 800; color: #F59E0B; margin-top: 4px;">
              ${escapeHtml(r.formatted_net_cogs || formatPkr(r.net_cogs_minor || 0))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">
              Restock Reversals: -${formatPkr(r.cogs_reversals_minor || 0)}
            </div>
          </div>

          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600;">Contribution Before Overhead</div>
            <div id="kpi-contribution" style="font-size: 1.4rem; font-weight: 800; color: #38BDF8; margin-top: 4px;">
              ${escapeHtml(r.formatted_contribution_before_overhead || formatPkr(r.contribution_before_overhead_minor || 0))}
            </div>
            <div style="font-size: 0.7rem; color: #38BDF8; font-weight: 700; margin-top: 4px;">
              ${(r.contribution_margin_pct ?? 0).toFixed(1)}% margin on net revenue
            </div>
          </div>

          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600;">Evidenced Logistics & Overhead</div>
            <div id="kpi-total-overhead" style="font-size: 1.4rem; font-weight: 800; color: #F87171; margin-top: 4px;">
              ${formatPkr((r.total_freight_minor || 0) + (r.total_overhead_minor || 0))}
            </div>
            <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.4); margin-top: 4px;">
              Freight: ${formatPkr(r.total_freight_minor || 0)} · Overhead: ${formatPkr(r.total_overhead_minor || 0)}
            </div>
          </div>

          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 14px;">
            <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; font-weight: 600;">Net Operating Result</div>
            <div id="kpi-operating-result" style="font-size: 1.4rem; font-weight: 800; color: ${(r.net_operating_result_minor || 0) >= 0 ? '#34D399' : '#F87171'}; margin-top: 4px;">
              ${escapeHtml(r.formatted_net_operating_result || formatPkr(r.net_operating_result_minor || 0))}
            </div>
            <div style="font-size: 0.7rem; color: ${(r.net_operating_result_minor || 0) >= 0 ? '#34D399' : '#F87171'}; font-weight: 700; margin-top: 4px;">
              ${(r.operating_margin_pct ?? 0).toFixed(1)}% operating margin
            </div>
          </div>

        </div>

        <!-- Section 1 & 2 Split: P&L Statement and Cash Movement -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
          
          <!-- Card 1: P&L Statement -->
          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 18px; display: flex; flex-direction: column; gap: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 10px;">
              <h4 style="font-size: 0.875rem; font-weight: 700; color: #FFFFFF; margin: 0;">Period Income Statement (P&L)</h4>
              <span style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.4); text-transform: uppercase;">Delivered basis</span>
            </div>

            <!-- Revenue Block -->
            <div style="font-size: 0.8125rem;">
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.45); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Revenue</div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Gross Delivered Sales</span>
                <span style="font-family: monospace;">${formatPkr(r.gross_revenue_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Customer Discounts</span>
                <span style="font-family: monospace; color: #F59E0B;">-${formatPkr(r.customer_discounts_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Customer Shipping Fee</span>
                <span style="font-family: monospace;">+${formatPkr(r.customer_shipping_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Completed Sales Reversals (Returns)</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr(r.sales_reversals_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 6px 0; border-top: 1px dashed rgba(255, 255, 255, 0.1); font-weight: 700;">
                <span style="color: #4ADE80;">Net Revenue</span>
                <span style="font-family: monospace; color: #4ADE80;">${formatPkr(r.net_revenue_minor || 0)}</span>
              </div>
            </div>

            <!-- COGS Block -->
            <div style="font-size: 0.8125rem; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px;">
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.45); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Cost of Goods Sold (COGS)</div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Wholesale Product Cost (Snapshot)</span>
                <span style="font-family: monospace;">${formatPkr(r.gross_cogs_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Sellable Return Restocks (COGS Reversals)</span>
                <span style="font-family: monospace; color: #4ADE80;">-${formatPkr(r.cogs_reversals_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 6px 0; border-top: 1px dashed rgba(255, 255, 255, 0.1); font-weight: 700;">
                <span style="color: #F59E0B;">Net Wholesale COGS</span>
                <span style="font-family: monospace; color: #F59E0B;">${formatPkr(r.net_cogs_minor || 0)}</span>
              </div>
            </div>

            <!-- Contribution Block -->
            <div style="background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 6px; padding: 10px 12px; font-size: 0.8125rem;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: 700; color: #38BDF8;">Contribution Before Overhead</div>
                  <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.5);">Net Revenue less Net COGS</div>
                </div>
                <div style="text-align: right;">
                  <div style="font-family: monospace; font-size: 1.1rem; font-weight: 800; color: #38BDF8;">${formatPkr(r.contribution_before_overhead_minor || 0)}</div>
                  <div style="font-size: 0.7rem; color: #38BDF8; font-weight: 600;">${(r.contribution_margin_pct ?? 0).toFixed(1)}% Margin</div>
                </div>
              </div>
            </div>

            <!-- Freight & Overhead Expenses Block -->
            <div style="font-size: 0.8125rem; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px;">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.45); text-transform: uppercase; font-weight: 700;">Evidenced Logistics & Overhead</span>
                <span style="font-size: 0.6875rem; color: #60A5FA; background: rgba(96, 165, 250, 0.15); padding: 1px 6px; border-radius: 4px; font-weight: 600;">AlphaZee-Borne Freight</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Outbound Courier Freight</span>
                <span style="font-family: monospace;">${formatPkr(r.outbound_freight_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">RTO Transport Freight (100% AlphaZee)</span>
                <span style="font-family: monospace; color: #F87171;">${formatPkr(r.rto_freight_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Customer Return Freight (100% AlphaZee)</span>
                <span style="font-family: monospace; color: #F87171;">${formatPkr(r.customer_return_freight_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Packaging & Boxes</span>
                <span style="font-family: monospace;">${formatPkr(overhead.packaging || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Advertising & Marketing</span>
                <span style="font-family: monospace;">${formatPkr(overhead.advertising || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Platform & Hosting</span>
                <span style="font-family: monospace;">${formatPkr(overhead.platform_hosting || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Salaries & Wages</span>
                <span style="font-family: monospace;">${formatPkr(overhead.salaries || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 3px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Office & Other Overhead</span>
                <span style="font-family: monospace;">${formatPkr((overhead.office_supplies || 0) + (overhead.other_overhead || 0))}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 6px 0; border-top: 1px dashed rgba(255, 255, 255, 0.1); font-weight: 700;">
                <span style="color: #F87171;">Total Evidenced Logistics & Overhead</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr((r.total_freight_minor || 0) + (r.total_overhead_minor || 0))}</span>
              </div>
            </div>

            <!-- Net Operating Result Block -->
            <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 12px; font-size: 0.8125rem;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: 800; color: #FFFFFF; font-size: 0.9375rem;">Net Operating Result</div>
                  <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.45); margin-top: 2px;">
                    Contribution less recorded transport & operational overhead
                  </div>
                </div>
                <div style="text-align: right;">
                  <div style="font-family: monospace; font-size: 1.25rem; font-weight: 800; color: ${(r.net_operating_result_minor || 0) >= 0 ? '#34D399' : '#F87171'};">
                    ${formatPkr(r.net_operating_result_minor || 0)}
                  </div>
                  <div style="font-size: 0.72rem; color: ${(r.net_operating_result_minor || 0) >= 0 ? '#34D399' : '#F87171'}; font-weight: 700;">
                    ${(r.operating_margin_pct ?? 0).toFixed(1)}% Operating Margin
                  </div>
                </div>
              </div>
              <div style="font-size: 0.6875rem; color: rgba(255, 255, 255, 0.4); margin-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 6px;">
                ⚠️ <strong>Disclosure:</strong> Net Operating Result is subject to unrecorded business expenses, tax liabilities, and pending courier settlements. Never treat as final audited net profit.
              </div>
            </div>

          </div>

          <!-- Card 2: Cash Movement & Balance Sheet -->
          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 18px; display: flex; flex-direction: column; gap: 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 10px;">
              <h4 style="font-size: 0.875rem; font-weight: 700; color: #FFFFFF; margin: 0;">Cash Movement & Account Reconciliation</h4>
              <span style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.4); text-transform: uppercase;">Realized cash flow</span>
            </div>

            <!-- Inflows Block -->
            <div style="font-size: 0.8125rem;">
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.45); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Cash Inflows (Actual Receipts)</div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Bank Customer Prepayments Cleared</span>
                <span style="font-family: monospace;">+${formatPkr(r.bank_prepayments_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Courier COD Cash Remitted into Bank</span>
                <span style="font-family: monospace;">+${formatPkr(r.courier_cod_remitted_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Supplier Refunds Received</span>
                <span style="font-family: monospace;">+${formatPkr(r.supplier_refunds_received_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 6px 0; border-top: 1px dashed rgba(255, 255, 255, 0.1); font-weight: 700;">
                <span style="color: #4ADE80;">Total Cash Inflows</span>
                <span style="font-family: monospace; color: #4ADE80;">${formatPkr(r.total_cash_inflows_minor || 0)}</span>
              </div>
            </div>

            <!-- Outflows Block -->
            <div style="font-size: 0.8125rem; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px;">
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.45); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Cash Outflows (Disbursements)</div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Supplier Payments Disbursed</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr(r.supplier_payments_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Customer Refunds Paid</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr(r.refunds_paid_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Direct Cash & Bank Expenses Paid</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr(r.cash_expenses_paid_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Courier Freight Deductions Settled</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr(r.courier_deductions_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 6px 0; border-top: 1px dashed rgba(255, 255, 255, 0.1); font-weight: 700;">
                <span style="color: #F87171;">Total Cash Outflows</span>
                <span style="font-family: monospace; color: #F87171;">-${formatPkr(r.total_cash_outflows_minor || 0)}</span>
              </div>
            </div>

            <!-- Net Cash Movement Block -->
            <div style="background: rgba(0, 0, 0, 0.3); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 12px; font-size: 0.8125rem;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                  <div style="font-weight: 800; color: #FFFFFF; font-size: 0.9375rem;">Net Cash Movement</div>
                  <div style="font-size: 0.7rem; color: rgba(255, 255, 255, 0.45); margin-top: 2px;">
                    Realized cash inflow less disbursed outflow
                  </div>
                </div>
                <div style="text-align: right;">
                  <div style="font-family: monospace; font-size: 1.25rem; font-weight: 800; color: ${(r.net_cash_movement_minor || 0) >= 0 ? '#4ADE80' : '#F87171'};">
                    ${formatPkr(r.net_cash_movement_minor || 0)}
                  </div>
                </div>
              </div>
            </div>

            <!-- Outstanding Receivables & Liabilities Block -->
            <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px; font-size: 0.8125rem;">
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.45); text-transform: uppercase; font-weight: 700; margin-bottom: 6px;">Outstanding Receivables & Liabilities</div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Courier-Held COD (Pending Remittance)</span>
                <span style="font-family: monospace; font-weight: 700; color: #FBBF24;">${formatPkr(r.courier_held_cod_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Outstanding Supplier Liabilities</span>
                <span style="font-family: monospace; font-weight: 700; color: #F87171;">${formatPkr(r.supplier_liabilities_minor || 0)}</span>
              </div>
              <div style="display: flex; justify-content: space-between; padding: 4px 0;">
                <span style="color: rgba(255, 255, 255, 0.75);">Customer Refund Liabilities Payable</span>
                <span style="font-family: monospace; font-weight: 700; color: #F87171;">${formatPkr(r.refund_liabilities_minor || 0)}</span>
              </div>
            </div>

          </div>

        </div>

        <!-- Section 3: Per-Order Economics & Margin Inspection -->
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 18px; display: flex; flex-direction: column; gap: 14px;">
          
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <div>
              <h4 style="font-size: 0.875rem; font-weight: 700; color: #FFFFFF; margin: 0 0 4px 0;">Per-Order Economics & Line-Item Margins</h4>
              <div style="font-size: 0.72rem; color: rgba(255, 255, 255, 0.5);">
                Inspect wholesale cost, outbound freight, RTO penalties, and stock ownership source per order.
              </div>
            </div>

            <!-- Order Table Filter Controls -->
            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
              <select id="report-order-status-filter" style="background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem;">
                <option value="" ${orderStatusFilter === '' ? 'selected' : ''}>All Order Statuses</option>
                <option value="delivered" ${orderStatusFilter === 'delivered' ? 'selected' : ''}>Delivered</option>
                <option value="dispatched" ${orderStatusFilter === 'dispatched' ? 'selected' : ''}>Dispatched</option>
                <option value="confirmed" ${orderStatusFilter === 'confirmed' ? 'selected' : ''}>Confirmed</option>
                <option value="placed" ${orderStatusFilter === 'placed' ? 'selected' : ''}>Placed</option>
                <option value="rto" ${orderStatusFilter === 'rto' ? 'selected' : ''}>RTO</option>
                <option value="cancelled" ${orderStatusFilter === 'cancelled' ? 'selected' : ''}>Cancelled</option>
              </select>

              <input type="text" id="report-order-search" placeholder="Search order # or customer..." value="${escapeHtml(orderSearchQuery)}" style="background: #111413; border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 4px; padding: 4px 8px; font-size: 0.75rem; width: 180px;" />

              <button type="button" id="btn-filter-orders" style="background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.2); color: #FFF; border-radius: 4px; padding: 4px 10px; font-size: 0.75rem; cursor: pointer;">
                Filter
              </button>
            </div>
          </div>

          <!-- Order Economics Table -->
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.12); font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; background: rgba(0, 0, 0, 0.2);">
                  <th style="padding: 10px 8px;">Order #</th>
                  <th style="padding: 10px 8px;">Customer</th>
                  <th style="padding: 10px 8px;">Status</th>
                  <th style="padding: 10px 8px; text-align: right;">Customer Total</th>
                  <th style="padding: 10px 8px; text-align: right;">COGS</th>
                  <th style="padding: 10px 8px; text-align: right;">Logistics</th>
                  <th style="padding: 10px 8px; text-align: right;">Supplier Payables</th>
                  <th style="padding: 10px 8px; text-align: right;">Est. Contribution</th>
                  <th style="padding: 10px 8px; text-align: center;">Lines</th>
                </tr>
              </thead>
              <tbody>
                ${ordersRowsHtml.length ? ordersRowsHtml : '<tr><td colspan="9" style="padding: 32px 8px; text-align: center; color: rgba(255,255,255,0.4);">No orders recorded for this period matching the selected criteria.</td></tr>'}
              </tbody>
            </table>
          </div>

          <!-- Total count and pagination -->
          <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); padding-top: 8px;">
            <div>Showing ${(orderEconomics.orders || []).length} of ${orderEconomics.total_orders || 0} orders</div>
            ${orderEconomics.total_orders > orderLimit ? `
              <div style="display: flex; gap: 6px;">
                <button type="button" id="btn-orders-prev" ${orderOffset === 0 ? 'disabled' : ''} style="padding: 3px 8px; font-size: 0.72rem; border-radius: 4px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #FFF; cursor: pointer;">Prev</button>
                <button type="button" id="btn-orders-next" ${orderOffset + orderLimit >= orderEconomics.total_orders ? 'disabled' : ''} style="padding: 3px 8px; font-size: 0.72rem; border-radius: 4px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); color: #FFF; cursor: pointer;">Next</button>
              </div>
            ` : ''}
          </div>

        </div>

        <!-- Section 4: Marketing Attribution & Campaign Conversion -->
        <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 18px; display: flex; flex-direction: column; gap: 12px;">
          <h4 style="font-size: 0.875rem; font-weight: 700; color: #FFFFFF; margin: 0;">Marketing Attribution & Campaign Conversion (UTM)</h4>
          <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; text-align: left;">
              <thead>
                <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1); font-size: 0.72rem; color: rgba(255, 255, 255, 0.5); text-transform: uppercase;">
                  <th style="padding: 8px;">UTM Source</th>
                  <th style="padding: 8px;">Medium</th>
                  <th style="padding: 8px;">Campaign</th>
                  <th style="padding: 8px; text-align: center;">Orders</th>
                  <th style="padding: 8px; text-align: right;">Delivered Sales</th>
                  <th style="padding: 8px; text-align: right;">Discounts</th>
                </tr>
              </thead>
              <tbody>
                ${marketingRowsHtml.length ? marketingRowsHtml : '<tr><td colspan="6" style="padding: 16px 8px; text-align: center; color: rgba(255,255,255,0.4);">No UTM attribution data recorded for this period.</td></tr>'}
              </tbody>
            </table>
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
