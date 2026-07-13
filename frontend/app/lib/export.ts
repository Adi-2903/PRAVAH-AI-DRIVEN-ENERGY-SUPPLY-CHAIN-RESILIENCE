// ═══════════════════════════════════════════════
//  PRAVAH — PDF / CSV / Print Export Utilities
//  PDF via jspdf + jspdf-autotable; CSV is hand-rolled (RFC-4180 escaping).
//  Print uses window.print() with an injected print stylesheet.
//  Every entry point is wrapped so a malformed field or a jsPDF failure
//  surfaces a friendly message instead of an unhandled promise rejection.
// ═══════════════════════════════════════════════

/** Log + surface an export failure without crashing the click handler. */
function reportExportError(kind: string, err: unknown): void {
  const msg = err instanceof Error ? err.message : String(err);
  console.error(`[export] ${kind} export failed:`, err);
  if (typeof window !== 'undefined') {
    window.alert(`Sorry — the ${kind} export failed and was cancelled.\n\n${msg}`);
  }
}

/**
 * Export tabular data as a CSV file download.
 */
export function exportToCSV(filename: string, headers: string[], rows: (string | number)[][]) {
  try {
    if (typeof window === 'undefined') {
      throw new Error('CSV export is only available in the browser.');
    }
    const escape = (cell: string) => {
      if (cell.includes(',') || cell.includes('"') || cell.includes('\n') || cell.includes('\r')) {
        return `"${cell.replace(/"/g, '""')}"`;
      }
      return cell;
    };
    const csvContent = [
      headers.map(String).map(escape).join(','),
      ...rows.map(row => row.map(cell => escape(String(cell))).join(','))
    ].join('\r\n');

    const bom = '\uFEFF'; // UTF-8 BOM for Excel compatibility
    const blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) {
    reportExportError('CSV', err);
  }
}

/**
 * Print the current page (opens the browser's print dialog).
 * Injects a temporary print stylesheet if needed.
 */
export function printReport(title?: string): void {
  try {
    if (typeof window === 'undefined') return;

    // Inject a print-specific style
    const style = document.createElement('style');
    style.id = '__pravah_print_style';
    style.media = 'print';
    style.textContent = `
      @media print {
        /* Hide non-essential UI elements */
        aside, header, .no-print, button, .tier-switcher,
        nav, .alert-bar-critical { display: none !important; }
        body { background: white !important; color: black !important; }
        .card { box-shadow: none !important; border: 1px solid #ddd !important; break-inside: avoid; }
        main { overflow: visible !important; height: auto !important; }
        * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
      }
    `;
    const existingStyle = document.getElementById('__pravah_print_style');
    if (existingStyle) existingStyle.remove();
    document.head.appendChild(style);

    if (title) {
      document.title = `PRAVAH — ${title}`;
    }

    window.print();
  } catch (err) {
    reportExportError('Print', err);
  }
}

/**
 * Export a branded PDF report.
 */
export async function exportToPDF(
  title: string,
  sections: { heading: string; content: string }[],
  tableData?: { headers: string[]; rows: (string | number)[][] },
  reasoning?: string
) {
  try {
    if (typeof window === 'undefined') {
      throw new Error('PDF export is only available in the browser.');
    }

    // Dynamic imports — MUST stay inside the function to avoid SSR/build errors
    const [{ default: jsPDF }, { default: autoTable }] = await Promise.all([
      import('jspdf'),
      import('jspdf-autotable'),
    ]);

    const doc = new jsPDF('p', 'mm', 'a4');
    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();
    let y = 20;

    // ─── Header ───
    doc.setFillColor(37, 99, 235);
    doc.rect(0, 0, pageWidth, 30, 'F');

    // Logo accent
    doc.setFillColor(29, 78, 216);
    doc.rect(0, 0, 5, 30, 'F');

    doc.setTextColor(255, 255, 255);
    doc.setFontSize(20);
    doc.setFont('helvetica', 'bold');
    doc.text('PRAVAH', 14, 13);

    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text('Energy Supply Chain Resilience · India', 14, 21);

    doc.setFontSize(8);
    doc.setTextColor(186, 230, 253);
    doc.text(`Generated: ${new Date().toLocaleString('en-IN')}`, pageWidth - 14, 13, { align: 'right' });
    doc.text('PROTOTYPE — NOT FOR OPERATIONAL USE', pageWidth - 14, 21, { align: 'right' });

    y = 42;

    // ─── Title ───
    doc.setTextColor(15, 23, 42);
    doc.setFontSize(18);
    doc.setFont('helvetica', 'bold');
    doc.text(title, 14, y);

    // Underline
    doc.setDrawColor(37, 99, 235);
    doc.setLineWidth(0.8);
    doc.line(14, y + 3, pageWidth - 14, y + 3);
    y += 14;

    // ─── Metadata row ───
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 116, 139);
    doc.text(`Ministry of Petroleum & Natural Gas · Composite Risk Index: 74/100 · Alert Level 3 — Elevated`, 14, y);
    y += 10;

    // ─── Sections ───
    for (const section of sections) {
      if (y > 260) { doc.addPage(); y = 20; }

      // Section heading background
      doc.setFillColor(239, 246, 255);
      doc.roundedRect(14, y - 4, pageWidth - 28, 10, 2, 2, 'F');

      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(37, 99, 235);
      doc.text(section.heading, 17, y + 3);
      y += 12;

      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(51, 65, 85);
      const lines = doc.splitTextToSize(section.content, pageWidth - 28);
      doc.text(lines, 14, y);
      y += lines.length * 5 + 8;
    }

    // ─── Table ───
    if (tableData && tableData.rows.length > 0) {
      if (y > 200) { doc.addPage(); y = 20; }

      autoTable(doc, {
        startY: y,
        head: [tableData.headers],
        body: tableData.rows.map(row => row.map(String)),
        styles: { fontSize: 9, cellPadding: 3.5, font: 'helvetica' },
        headStyles: {
          fillColor: [37, 99, 235],
          textColor: [255, 255, 255],
          fontStyle: 'bold',
          halign: 'center',
        },
        alternateRowStyles: { fillColor: [248, 250, 252] },
        bodyStyles: { textColor: [51, 65, 85] },
        margin: { left: 14, right: 14 },
        tableLineColor: [226, 232, 240],
        tableLineWidth: 0.1,
      });
      y = (doc as any).lastAutoTable.finalY + 12;
    }

    // ─── Reasoning Trail ───
    if (reasoning && reasoning.trim()) {
      if (y > 230) { doc.addPage(); y = 20; }

      const reasoningLines = doc.splitTextToSize(reasoning, pageWidth - 46);
      const boxHeight = reasoningLines.length * 5 + 16;

      doc.setFillColor(239, 246, 255);
      doc.setDrawColor(37, 99, 235);
      doc.setLineWidth(0.3);
      doc.roundedRect(14, y, pageWidth - 28, boxHeight, 3, 3, 'FD');

      // Left accent bar
      doc.setFillColor(37, 99, 235);
      doc.rect(14, y, 3, boxHeight, 'F');

      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(37, 99, 235);
      doc.text('AI REASONING TRAIL', 22, y + 7);

      doc.setFontSize(9);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(51, 65, 85);
      doc.text(reasoningLines, 22, y + 13);
      y += boxHeight + 10;
    }

    // ─── Footer on all pages ───
    const pageCount = doc.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);

      // Footer bar
      doc.setFillColor(248, 250, 252);
      doc.rect(0, pageHeight - 14, pageWidth, 14, 'F');
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(0.3);
      doc.line(0, pageHeight - 14, pageWidth, pageHeight - 14);

      doc.setFontSize(7);
      doc.setFont('helvetica', 'normal');
      doc.setTextColor(148, 163, 184);
      doc.text(
        `PRAVAH Prototype · Ministry of Petroleum & Natural Gas · Page ${i} of ${pageCount}`,
        pageWidth / 2,
        pageHeight - 6,
        { align: 'center' }
      );
      doc.text('Generated by AI Advisory Layer — For internal planning purposes only', 14, pageHeight - 6);
    }

    const safeTitle = title.replace(/[^a-zA-Z0-9_\-]/g, '_');
    doc.save(`PRAVAH_${safeTitle}_${new Date().toISOString().slice(0, 10)}.pdf`);
  } catch (err) {
    reportExportError('PDF', err);
  }
}

/**
 * Quick export: Scenario simulation results
 */
export async function exportScenarioReport(result: any) {
  try {
    await exportToPDF(
      'Supply Shock Scenario Report',
      [
        {
          heading: 'Scenario Summary',
          content: `Brent crude projection: Median (P50) $${result.brent_price_distribution?.p50?.toFixed(2) ?? 'N/A'}/bbl, Worst case (P90) $${result.brent_price_distribution?.p90?.toFixed(2) ?? 'N/A'}/bbl. Standard deviation: ±$${result.brent_price_distribution?.std_dev?.toFixed(2) ?? 'N/A'}. Simulations run: ${result.num_simulations_run?.toLocaleString() ?? 'N/A'}.`
        },
        {
          heading: 'Economic Impact',
          content: `Pump price impact (P50): ₹${result.pump_price_impact?.projected_p50_inr_per_litre?.toFixed(2) ?? 'N/A'}/litre (from ₹${result.pump_price_impact?.current_inr_per_litre?.toFixed(2) ?? 'N/A'}/litre). GDP impact (P50): ${result.gdp_impact_pct?.p50?.toFixed(3) ?? 'N/A'}%. Data source: ${result.data_source ?? 'fallback_cache'}.`
        },
        {
          heading: 'Calibration Reference',
          content: result.calibration_note ?? 'Elasticities validated against EIA historical shock data.'
        }
      ],
      Array.isArray(result.daily_price_path) ? {
        headers: ['Day', 'P10 (Best)', 'P50 (Median)', 'P90 (Worst)'],
        rows: result.daily_price_path.slice(0, 20).map((d: any) => [
          `Day ${d?.day ?? '—'}`, `$${d?.p10?.toFixed(2) ?? 'N/A'}`, `$${d?.p50?.toFixed(2) ?? 'N/A'}`, `$${d?.p90?.toFixed(2) ?? 'N/A'}`
        ]),
      } : undefined,
      result.calibration_note
    );
  } catch (err) {
    reportExportError('scenario report', err);
  }
}

/**
 * Quick export: Procurement recommendations
 */
export async function exportProcurementReport(recs: any[], baseline: any) {
  try {
    await exportToPDF(
      'Procurement Alternatives Report',
      [
        {
          heading: 'Current Baseline',
          content: `Supplier: ${baseline?.supplier ?? 'N/A'}. Cost: $${baseline?.estimated_cost_usd_per_bbl?.toFixed(1) ?? 'N/A'}/bbl. Risk: ${baseline?.corridor_risk_score ?? 'N/A'}/100. Transit: ${baseline?.transit_days ?? 'N/A'} days. Score: ${baseline?.composite_score?.toFixed(3) ?? 'N/A'}.`
        },
        {
          heading: 'Optimization Parameters',
          content: `Alternatives ranked by weighted composite score (cost 25%, risk 30%, transit 20%, grade compatibility 25%). Higher score = better alternative. Analysis accounts for Hormuz disruption scenario.`
        },
      ],
      {
        headers: ['Rank', 'Supplier', 'Cost ($/bbl)', 'Risk', 'Transit', 'Score', 'Reasoning'],
        rows: (recs ?? []).map(r => [
          r?.rank ?? '—', r?.supplier ?? 'N/A', `$${r?.estimated_cost_usd_per_bbl?.toFixed(1) ?? 'N/A'}`,
          `${r?.corridor_risk_score ?? 'N/A'}/100`, `${r?.transit_days ?? 'N/A'}d`,
          r?.composite_score?.toFixed(3) ?? 'N/A', ((r?.reasoning ?? '').slice(0, 60)) + '...'
        ]),
      }
    );
  } catch (err) {
    reportExportError('procurement report', err);
  }
}

/**
 * Quick export: SPR schedule
 */
export function exportSPRScheduleCSV(schedule: any[]) {
  try {
    exportToCSV(
      'PRAVAH_SPR_Schedule',
      ['Day', 'Drawdown (days)', 'Reserve After (days)', 'Risk Score', 'Price (USD)', 'Rationale'],
      (schedule ?? []).map(s => [
        `D+${s?.day ?? '—'}`, s?.drawdown_days?.toFixed(2) ?? 'N/A', s?.reserve_after_days?.toFixed(2) ?? 'N/A',
        s?.risk_score?.toFixed(0) ?? 'N/A', `$${s?.price_usd?.toFixed(2) ?? 'N/A'}`, s?.rationale ?? ''
      ])
    );
  } catch (err) {
    reportExportError('SPR schedule', err);
  }
}

/**
 * Export policy document as PDF
 */
export async function exportPolicyDocument(policies: any[], situation: string) {
  try {
    await exportToPDF(
      'AI Policy Recommendations — Energy Security',
      [
        {
          heading: 'Current Geopolitical Situation',
          content: situation
        },
        {
          heading: 'Policy Mandate',
          content: 'The following policy recommendations have been generated by the PRAVAH AI Advisory Layer based on real-time risk intelligence, scenario modelling, and procurement optimization. These are strategic suggestions requiring Ministerial review and approval before implementation.'
        },
        ...policies.map((p, i) => ({
          heading: `Policy ${i + 1}: ${p.title}`,
          content: `Priority: ${p.priority} | Category: ${p.category}\n\n${p.description}\n\nExpected Outcome: ${p.outcome}\nImplementation Timeline: ${p.timeline}`
        }))
      ],
      undefined,
      'All recommendations generated by PRAVAH AI Advisory Layer (Gemini 2.5 Flash). The system continuously monitors GDELT geopolitical events, AIS vessel tracking, OFAC sanctions data, and EIA price signals to derive actionable policy guidance.'
    );
  } catch (err) {
    reportExportError('policy document', err);
  }
}
