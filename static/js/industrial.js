/**
 * static/js/industrial.js
 *
 * ODIN On-Premise Industrial Intelligence Modals (SIH26117):
 *  1. P&ID Drawing Inspector & ISA-5.1 Loop Analyzer
 *  2. Merkle DAG Tamper-Evident Forensic Audit Trail Viewer
 */

let pidModalEl = null;
let auditModalEl = null;

export function openPIDInspector() {
  if (!pidModalEl) {
    createPIDModal();
  }
  pidModalEl.classList.remove('hidden');
  pidModalEl.style.display = 'flex';
}

export function closePIDInspector() {
  if (pidModalEl) {
    pidModalEl.classList.add('hidden');
    pidModalEl.style.display = 'none';
  }
}

export function openAuditTrail() {
  if (!auditModalEl) {
    createAuditModal();
  }
  auditModalEl.classList.remove('hidden');
  auditModalEl.style.display = 'flex';
  loadAuditStatsAndBlocks();
}

export function closeAuditTrail() {
  if (auditModalEl) {
    auditModalEl.classList.add('hidden');
    auditModalEl.style.display = 'none';
  }
}

function createPIDModal() {
  pidModalEl = document.createElement('div');
  pidModalEl.id = 'pid-inspector-modal';
  pidModalEl.className = 'modal';
  pidModalEl.style.cssText = `
    display: flex;
    position: fixed;
    inset: 0;
    z-index: 10000;
    background: rgba(0,0,0,0.65);
    backdrop-filter: blur(8px);
    align-items: center;
    justify-content: center;
  `;

  pidModalEl.innerHTML = `
    <div class="modal-content" style="
      background: var(--panel, #1e222b);
      color: var(--fg, #abb2bf);
      border: 1px solid var(--border, #333842);
      border-radius: 12px;
      width: 900px;
      max-width: 95vw;
      max-height: 88vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
      overflow: hidden;
      font-family: inherit;
    ">
      <!-- Header -->
      <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid var(--border, #333842);
        background: rgba(255,255,255,0.02);
      ">
        <div style="display: flex; align-items: center; gap: 10px;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary, #0284c7)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M6 9v12"/><path d="M18 3v12"/><path d="M9 12h6"/>
          </svg>
          <span style="font-weight: 700; font-size: 16px; color: var(--fg, #abb2bf);">
            P&ID Drawing &amp; Instrument Inspector
          </span>
          <span style="
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 4px;
            background: rgba(2, 132, 199, 0.15);
            color: var(--color-primary, #38bdf8);
            border: 1px solid rgba(2, 132, 199, 0.3);
            font-weight: 600;
          ">
            ISA-5.1 / HAZOP
          </span>
          <span style="
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 4px;
            background: rgba(34, 197, 94, 0.12);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.25);
            font-weight: 600;
          ">
            0-WAN AIR-GAP
          </span>
        </div>
        <button id="close-pid-modal-btn" style="
          background: transparent;
          border: none;
          color: var(--fg, #abb2bf);
          cursor: pointer;
          font-size: 20px;
          line-height: 1;
          padding: 4px 8px;
          border-radius: 4px;
          opacity: 0.7;
        ">&times;</button>
      </div>

      <!-- Body -->
      <div style="padding: 20px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 16px;">
        <div style="font-size: 13px; opacity: 0.8; line-height: 1.5;">
          Inspect piping and instrumentation schematics for MRPL process units. Automatically parses instrument loops (FT, FIC, PT, PSV, TT, LT), equipment numbers (C-101, V-102, P-101A/B, E-201), Barlow line sizes, and flags regulatory safety discrepancies.
        </div>

        <div style="display: flex; gap: 10px; align-items: center;">
          <input type="text" id="pid-drawing-id-input" value="MRPL-CDU-VDU-101-P&amp;ID" style="
            background: rgba(0,0,0,0.25);
            border: 1px solid var(--border, #333842);
            color: inherit;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 13px;
            width: 260px;
          " placeholder="Drawing Tag / Name">
          
          <button id="pid-load-sample-btn" style="
            background: rgba(255,255,255,0.06);
            border: 1px solid var(--border, #333842);
            color: inherit;
            padding: 8px 14px;
            border-radius: 6px;
            font-size: 12px;
            cursor: pointer;
          ">Load Refinery Sample</button>

          <button id="pid-run-inspect-btn" style="
            background: var(--color-primary, #0284c7);
            color: #fff;
            border: none;
            padding: 8px 18px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            margin-left: auto;
            display: inline-flex;
            align-items: center;
            gap: 6px;
          ">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
            Inspect P&amp;ID
          </button>
        </div>

        <div>
          <label style="font-size: 12px; font-weight: 600; margin-bottom: 6px; display: block; opacity: 0.9;">
            P&amp;ID Drawing Content / Scanned OCR Stream:
          </label>
          <textarea id="pid-drawing-text" rows="7" style="
            width: 100%;
            box-sizing: border-box;
            background: rgba(0,0,0,0.3);
            border: 1px solid var(--border, #333842);
            color: inherit;
            padding: 12px;
            border-radius: 6px;
            font-family: monospace;
            font-size: 12px;
            resize: vertical;
          " placeholder="Paste P&amp;ID OCR tags or equipment specifications..."></textarea>
        </div>

        <div id="pid-results-container" style="display: none; flex-direction: column; gap: 14px;">
          <!-- Results injected here -->
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(pidModalEl);

  // Wire events
  pidModalEl.querySelector('#close-pid-modal-btn').addEventListener('click', closePIDInspector);
  pidModalEl.addEventListener('click', (e) => {
    if (e.target === pidModalEl) closePIDInspector();
  });

  const sampleBtn = pidModalEl.querySelector('#pid-load-sample-btn');
  const textArea = pidModalEl.querySelector('#pid-drawing-text');
  sampleBtn.addEventListener('click', () => {
    textArea.value = `MRPL REFINERY UNIT 01 - ATMOSPHERIC CRUDE DISTILLATION UNIT (CDU)
MAIN FRACTIONATOR COLUMN: C-101
CRUDE CHARGE ACCUMULATOR: V-102
FURNACE CHARGE PUMPS: P-101A, P-101B (CENTRIFUGAL)
CRUDE PREHEAT EXCHANGER TRAIN: E-201, E-202A/B
OVERHEAD RELIEF SAFETY VALVE: PSV-101A (SET 4.5 BARG)
REFLUX DRUM RELIEF VALVE: PSV-102 (SET 3.2 BARG)
INSTRUMENTATION LOOPS:
  - FLOW CONTROLLER: FIC-101 (ORIFICE FE-101, VALVE FCV-101)
  - COLUMN OVERHEAD PRESSURE: PIC-102 (TRANSMITTER PT-102, VALVE PCV-102)
  - REFLUX DRUM LEVEL: LIC-103 (TRANSMITTER LT-103, VALVE LCV-103)
  - COLUMN TOP TEMPERATURE: TIC-104 (TRANSMITTER TT-104, VALVE TCV-104)
PROCESS PIPING LINES:
  - CRUDE FEED LINE: 10"-CRU-1001-A1A
  - COLUMN OVERHEAD VAPOR: 14"-VAP-1002-CS
  - REFLUX LIQUID: 6"-HC-1003-B2B
  - RESIDUE BOTTOMS: 8"-RES-1004-C1A`;
  });

  const runBtn = pidModalEl.querySelector('#pid-run-inspect-btn');
  const resultsContainer = pidModalEl.querySelector('#pid-results-container');

  runBtn.addEventListener('click', async () => {
    const text = textArea.value.trim();
    const drawingId = pidModalEl.querySelector('#pid-drawing-id-input').value.trim();
    if (!text) {
      alert('Please enter or load P&ID drawing text to inspect.');
      return;
    }

    runBtn.disabled = true;
    runBtn.textContent = 'Inspecting...';

    try {
      const res = await fetch('/api/industrial/pid/parse_text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ drawing_text: text, drawing_id: drawingId }),
      });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${await res.text()}`);
      }
      const data = await res.json();
      renderPIDResults(data, resultsContainer);
    } catch (err) {
      alert(`Inspection failed: ${err.message}`);
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg> Inspect P&amp;ID`;
    }
  });
}

function renderPIDResults(data, container) {
  container.style.display = 'flex';
  const ent = data.entities || {};
  const sum = ent.summary || {};
  const discs = data.discrepancies || [];

  let discsHtml = '';
  if (discs.length === 0) {
    discsHtml = `
      <div style="padding: 10px 14px; border-radius: 6px; background: rgba(34, 197, 94, 0.12); border: 1px solid rgba(34, 197, 94, 0.3); color: #4ade80; font-size: 12px; display: flex; align-items: center; gap: 8px;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg>
        <span>No HAZOP or safety discrepancies detected. Regulatory relief valves and isolation systems verified.</span>
      </div>
    `;
  } else {
    discsHtml = discs.map(d => {
      const isCrit = d.severity === 'CRITICAL';
      const color = isCrit ? '#f87171' : (d.severity === 'WARNING' ? '#fbbf24' : '#38bdf8');
      const bg = isCrit ? 'rgba(239, 68, 68, 0.12)' : 'rgba(245, 158, 11, 0.12)';
      const border = isCrit ? 'rgba(239, 68, 68, 0.3)' : 'rgba(245, 158, 11, 0.3)';
      return `
        <div style="padding: 10px 14px; border-radius: 6px; background: ${bg}; border: 1px solid ${border}; color: ${color}; font-size: 12px; margin-bottom: 6px;">
          <div style="font-weight: 700; margin-bottom: 2px;">[${d.severity}] ${d.rule}</div>
          <div>${d.description}</div>
          <div style="margin-top: 4px; font-size: 11px; opacity: 0.9;"><strong>Recommendation:</strong> ${d.recommendation}</div>
        </div>
      `;
    }).join('');
  }

  const instList = (ent.instruments || []).map(i => `
    <span style="display:inline-flex; align-items:center; gap:4px; padding:3px 8px; border-radius:4px; font-size:11px; font-family:monospace; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); margin:2px;">
      <strong style="color:${i.category === 'SAFETY' ? '#f87171' : 'var(--color-primary,#38bdf8)'}">${i.tag}</strong> (${i.type})
    </span>
  `).join('');

  const eqList = (ent.equipment || []).map(e => `
    <span style="display:inline-flex; align-items:center; gap:4px; padding:3px 8px; border-radius:4px; font-size:11px; font-family:monospace; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); margin:2px;">
      <strong>${e.tag}</strong> (${e.equipment_type})
    </span>
  `).join('');

  const linesList = (ent.piping_lines || []).map(l => `
    <span style="display:inline-flex; align-items:center; gap:4px; padding:3px 8px; border-radius:4px; font-size:11px; font-family:monospace; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1); margin:2px;">
      ${l.line_number}
    </span>
  `).join('');

  container.innerHTML = `
    <!-- Stats Bar -->
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;">
      <div style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.25); border: 1px solid var(--border,#333842); text-align: center;">
        <div style="font-size: 20px; font-weight: 700; color: var(--color-primary, #38bdf8);">${sum.total_instruments || 0}</div>
        <div style="font-size: 11px; opacity: 0.7;">ISA-5.1 Loops</div>
      </div>
      <div style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.25); border: 1px solid var(--border,#333842); text-align: center;">
        <div style="font-size: 20px; font-weight: 700; color: #a78bfa;">${sum.total_equipment || 0}</div>
        <div style="font-size: 11px; opacity: 0.7;">Major Equipment</div>
      </div>
      <div style="padding: 12px; border-radius: 8px; background: rgba(0,0,0,0.25); border: 1px solid var(--border,#333842); text-align: center;">
        <div style="font-size: 20px; font-weight: 700; color: #34d399;">${sum.total_process_lines || 0}</div>
        <div style="font-size: 11px; opacity: 0.7;">Barlow Process Lines</div>
      </div>
    </div>

    <!-- HAZOP Discrepancies -->
    <div style="background: rgba(0,0,0,0.2); border: 1px solid var(--border,#333842); border-radius: 8px; padding: 14px;">
      <div style="font-size: 13px; font-weight: 700; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        HAZOP &amp; Safety Discrepancies (${discs.length})
      </div>
      ${discsHtml}
    </div>

    <!-- Entities -->
    <div style="display: flex; flex-direction: column; gap: 8px;">
      <div style="font-size: 12px; font-weight: 600; opacity: 0.9;">Extracted Instrument Tags:</div>
      <div>${instList || '<span style="opacity:0.5;font-size:11px;">None</span>'}</div>
      
      <div style="font-size: 12px; font-weight: 600; opacity: 0.9; margin-top: 6px;">Extracted Major Equipment:</div>
      <div>${eqList || '<span style="opacity:0.5;font-size:11px;">None</span>'}</div>

      <div style="font-size: 12px; font-weight: 600; opacity: 0.9; margin-top: 6px;">Process Piping Lines:</div>
      <div>${linesList || '<span style="opacity:0.5;font-size:11px;">None</span>'}</div>
    </div>

    <div style="font-size: 11px; opacity: 0.6; display: flex; align-items: center; gap: 6px; margin-top: 6px;">
      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
      Cryptographically logged to Merkle DAG Audit Trail under action <code>INSPECT_PID_DRAWING</code>.
    </div>
  `;
}

function createAuditModal() {
  auditModalEl = document.createElement('div');
  auditModalEl.id = 'merkle-audit-modal';
  auditModalEl.className = 'modal';
  auditModalEl.style.cssText = `
    display: flex;
    position: fixed;
    inset: 0;
    z-index: 10000;
    background: rgba(0,0,0,0.65);
    backdrop-filter: blur(8px);
    align-items: center;
    justify-content: center;
  `;

  auditModalEl.innerHTML = `
    <div class="modal-content" style="
      background: var(--panel, #1e222b);
      color: var(--fg, #abb2bf);
      border: 1px solid var(--border, #333842);
      border-radius: 12px;
      width: 960px;
      max-width: 95vw;
      max-height: 88vh;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
      overflow: hidden;
      font-family: inherit;
    ">
      <!-- Header -->
      <div style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid var(--border, #333842);
        background: rgba(255,255,255,0.02);
      ">
        <div style="display: flex; align-items: center; gap: 10px;">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#34d399" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>
          </svg>
          <span style="font-weight: 700; font-size: 16px; color: var(--fg, #abb2bf);">
            Merkle DAG Forensic Audit Trail
          </span>
          <span style="
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 4px;
            background: rgba(52, 211, 153, 0.15);
            color: #34d399;
            border: 1px solid rgba(52, 211, 153, 0.3);
            font-weight: 600;
          ">
            SHA-256 TAMPER-EVIDENT
          </span>
          <span style="
            font-size: 10px;
            padding: 2px 7px;
            border-radius: 4px;
            background: rgba(2, 132, 199, 0.15);
            color: var(--color-primary, #38bdf8);
            border: 1px solid rgba(2, 132, 199, 0.3);
            font-weight: 600;
          ">
            0-WAN AIR-GAP ENFORCED
          </span>
        </div>
        <button id="close-audit-modal-btn" style="
          background: transparent;
          border: none;
          color: var(--fg, #abb2bf);
          cursor: pointer;
          font-size: 20px;
          line-height: 1;
          padding: 4px 8px;
          border-radius: 4px;
          opacity: 0.7;
        ">&times;</button>
      </div>

      <!-- Body -->
      <div style="padding: 20px; overflow-y: auto; flex: 1; display: flex; flex-direction: column; gap: 16px;">
        <!-- Top Stats / Root Digest -->
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;" id="audit-stats-row">
          <div style="padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,0.25); border: 1px solid var(--border,#333842);">
            <div style="font-size: 11px; opacity: 0.7; margin-bottom: 4px;">Cryptographic Blocks</div>
            <div style="font-size: 22px; font-weight: 700; color: #34d399;" id="audit-block-count">-</div>
          </div>
          <div style="padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,0.25); border: 1px solid var(--border,#333842);">
            <div style="font-size: 11px; opacity: 0.7; margin-bottom: 4px;">Integrity Verification</div>
            <div style="font-size: 15px; font-weight: 700; color: #38bdf8;" id="audit-integrity-status">Checking...</div>
          </div>
          <div style="padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,0.25); border: 1px solid var(--border,#333842);">
            <div style="font-size: 11px; opacity: 0.7; margin-bottom: 4px;">Air-Gap Egress</div>
            <div style="font-size: 13px; font-weight: 600; color: #4ade80;">0-WAN VERIFIED</div>
          </div>
        </div>

        <!-- Merkle Root Banner -->
        <div style="padding: 12px 16px; border-radius: 8px; background: rgba(0,0,0,0.35); border: 1px solid var(--border,#333842); display: flex; align-items: center; justify-content: space-between;">
          <div>
            <div style="font-size: 11px; opacity: 0.7; margin-bottom: 2px;">Current Merkle Root (SHA-256):</div>
            <div style="font-family: monospace; font-size: 12px; color: #fbbf24; word-break: break-all;" id="audit-merkle-root">
              Computing...
            </div>
          </div>
          <div style="display: flex; gap: 8px;">
            <button id="audit-verify-chain-btn" style="
              background: rgba(52, 211, 153, 0.15);
              color: #34d399;
              border: 1px solid rgba(52, 211, 153, 0.35);
              padding: 6px 14px;
              border-radius: 6px;
              font-size: 12px;
              cursor: pointer;
              font-weight: 600;
              display: inline-flex;
              align-items: center;
              gap: 6px;
            ">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>
              Verify Chain
            </button>
            <button id="audit-export-json-btn" style="
              background: rgba(255, 255, 255, 0.06);
              color: inherit;
              border: 1px solid var(--border, #333842);
              padding: 6px 12px;
              border-radius: 6px;
              font-size: 12px;
              cursor: pointer;
            ">
              Export JSON
            </button>
          </div>
        </div>

        <!-- Block Ledger Table -->
        <div style="display: flex; flex-direction: column; gap: 8px;">
          <div style="font-size: 13px; font-weight: 700; opacity: 0.9;">Cryptographically Chained Audit Ledger:</div>
          <div id="audit-blocks-list" style="
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 420px;
            overflow-y: auto;
          ">
            <!-- Blocks rendered here -->
          </div>
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(auditModalEl);

  // Wire events
  auditModalEl.querySelector('#close-audit-modal-btn').addEventListener('click', closeAuditTrail);
  auditModalEl.addEventListener('click', (e) => {
    if (e.target === auditModalEl) closeAuditTrail();
  });

  auditModalEl.querySelector('#audit-verify-chain-btn').addEventListener('click', async () => {
    try {
      const res = await fetch('/api/audit/verify');
      const data = await res.json();
      if (data.is_valid) {
        alert(`Cryptographic Audit Chain Integrity Verified!\nTotal Blocks: ${data.total_blocks_verified}\nMerkle Root: ${data.merkle_root}\nStatus: ${data.compliance_status}`);
      } else {
        alert(`TAMPERING DETECTED in Audit Trail:\n${JSON.stringify(data.discrepancies, null, 2)}`);
      }
    } catch (e) {
      alert(`Verification failed: ${e.message}`);
    }
  });

  auditModalEl.querySelector('#audit-export-json-btn').addEventListener('click', () => {
    window.open('/api/audit/export', '_blank');
  });
}

async function loadAuditStatsAndBlocks() {
  if (!auditModalEl) return;
  try {
    const [statsRes, blocksRes] = await Promise.all([
      fetch('/api/audit/stats'),
      fetch('/api/audit/blocks?limit=50'),
    ]);

    const stats = await statsRes.json();
    const blocksData = await blocksRes.json();

    document.getElementById('audit-block-count').textContent = stats.total_blocks ?? 0;
    document.getElementById('audit-merkle-root').textContent = stats.merkle_root || 'None';
    
    const isVal = stats.chain_valid;
    const intEl = document.getElementById('audit-integrity-status');
    intEl.textContent = isVal ? 'VALID & VERIFIED' : 'TAMPER EVIDENT';
    intEl.style.color = isVal ? '#34d399' : '#f87171';

    renderAuditBlocks(blocksData.blocks || []);
  } catch (err) {
    console.error('Failed to load audit trail:', err);
  }
}

function renderAuditBlocks(blocks) {
  const container = document.getElementById('audit-blocks-list');
  if (!container) return;

  if (blocks.length === 0) {
    container.innerHTML = '<div style="padding:16px;text-align:center;opacity:0.5;font-size:12px;">No audit events recorded yet.</div>';
    return;
  }

  container.innerHTML = blocks.map(b => {
    const prevHashShort = b.previous_hash ? b.previous_hash.slice(0, 12) + '...' : 'GENESIS';
    const currHashShort = b.block_hash ? b.block_hash.slice(0, 16) + '...' : '-';
    return `
      <div style="
        padding: 12px 14px;
        background: rgba(0,0,0,0.22);
        border: 1px solid var(--border, #333842);
        border-radius: 6px;
        display: flex;
        flex-direction: column;
        gap: 6px;
        font-size: 12px;
      ">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: 700; color: #34d399;">#${b.index}</span>
            <span style="font-weight: 600; color: #fff;">${b.action}</span>
            <span style="font-size: 10px; padding: 1px 6px; border-radius: 3px; background: rgba(255,255,255,0.06);">${b.department || 'OPERATIONS'}</span>
            <span style="font-size: 10px; color: #4ade80;">[${b.egress_status || '0-WAN'}]</span>
          </div>
          <div style="font-size: 11px; opacity: 0.6;">${b.timestamp}</div>
        </div>
        <div style="display: flex; align-items: center; justify-content: space-between; font-family: monospace; font-size: 11px; opacity: 0.8;">
          <div><span style="opacity:0.5;">Block:</span> <span style="color:#38bdf8;">${currHashShort}</span></div>
          <div><span style="opacity:0.5;">Prev:</span> <span style="color:#a78bfa;">${prevHashShort}</span></div>
          <div><span style="opacity:0.5;">User:</span> ${b.user || 'system'}</div>
        </div>
      </div>
    `;
  }).join('');
}
