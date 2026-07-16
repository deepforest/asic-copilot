import React, { useState, useMemo } from 'react'
import { Database, FileText, Activity, AlertOctagon, Search, Cpu } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Line,
  ReferenceLine
} from 'recharts'

function DataBrowser({
  activeTab,
  setActiveTab,
  spec,
  yieldData,
  telemetry,
  activeChip,
  setActiveChip
}) {
  const [searchTerm, setSearchTerm] = useState('')

  // 1. Yield Table Calculations
  const yieldStats = useMemo(() => {
    if (!yieldData || yieldData.length === 0) return null
    const leakages = yieldData.map(r => r.Static_Leakage_Power)
    const mean = leakages.reduce((a, b) => a + b, 0) / leakages.length
    const sqDiff = leakages.map(l => Math.pow(l - mean, 2))
    const variance = sqDiff.reduce((a, b) => a + b, 0) / (sqDiff.length - 1)
    const stdDev = Math.sqrt(variance)
    const threshold3s = mean + 3 * stdDev
    return { mean, stdDev, threshold3s }
  }, [yieldData])

  const filteredYield = useMemo(() => {
    return yieldData.filter(row => 
      row.Chip_ID.toLowerCase().includes(searchTerm.toLowerCase()) ||
      row.Corner.toLowerCase().includes(searchTerm.toLowerCase()) ||
      row.Wafer_ID.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [yieldData, searchTerm])

  // Custom tool tip for Telemetry Chart
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      // Format timestamp to simple seconds offset or local time
      const timeOffset = label - 1710500000
      return (
        <div className="chart-tooltip glass-card">
          <p className="tooltip-time">Time: +{timeOffset}s</p>
          {payload.map((pld, index) => (
            <p key={index} style={{ color: pld.color, fontSize: '0.8rem', margin: '2px 0' }}>
              {pld.name}: <strong>{pld.value} {pld.name.includes('Temp') ? '°C' : pld.name.includes('Volt') ? 'V' : 'W'}</strong>
            </p>
          ))}
        </div>
      )
    }
    return null
  }

  return (
    <div className="data-browser">
      <div className="tab-content-container">

        {/* Tab 2: Design Specifications */}
        {activeTab === 'specs' && (
          <div className="tab-pane spec-pane animate-fade">
            <div className="glass-card spec-card">
              <h2 className="spec-title">CX8 ASIC Design Constraints (Rev B0)</h2>
              <div className="spec-grid">
                <div className="spec-item">
                  <span>Core Voltage Supply (V_dd)</span>
                  <strong>0.8V</strong>
                  <p className="spec-desc">Nominal operating voltage for characterization testing.</p>
                </div>
                <div className="spec-item">
                  <span>Max Junction Temp (T_jmax)</span>
                  <strong className="text-red">105.0°C</strong>
                  <p className="spec-desc">Critical safety limit; exceeding causes physical overstress.</p>
                </div>
                <div className="spec-item">
                  <span>Max Static Leakage (P_leakage_max)</span>
                  <strong>12.5W</strong>
                  <p className="spec-desc">Hard design leakage budget. Outliers fail characterization.</p>
                </div>
                <div className="spec-item">
                  <span>Thermal Throttling Trigger</span>
                  <strong className="text-orange">98.0°C</strong>
                  <p className="spec-desc">Dynamic safety loop point where clocks scale back core power.</p>
                </div>
              </div>
              
              <div className="spec-raw">
                <h4>Raw Spec Document: `asic_spec.md`</h4>
                <pre>{spec?.raw_markdown || '# Loading spec...'}</pre>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Wafer Yield Data */}
        {activeTab === 'yield' && (
          <div className="tab-pane yield-pane animate-fade">
            {/* Stats Summary Panel */}
            {yieldStats && (
              <div className="yield-summary-panel glass-card">
                <div>
                  <span>Wafers Sampled:</span>
                  <strong>5 Wafers (WF_09, WF_12, WF_05, WF_17, WF_21)</strong>
                </div>
                <div>
                  <span>Mean Leakage (μ):</span>
                  <strong>{yieldStats.mean.toFixed(2)} W</strong>
                </div>
                <div>
                  <span>Standard Deviation (σ):</span>
                  <strong>{yieldStats.stdDev.toFixed(2)} W</strong>
                </div>
                <div>
                  <span>3σ Outlier Cutoff:</span>
                  <strong className="text-orange">{yieldStats.threshold3s.toFixed(2)} W</strong>
                </div>
              </div>
            )}

            {/* Toolbar */}
            <div className="yield-toolbar">
              <div className="search-bar">
                <Search size={16} className="text-muted" />
                <input 
                  type="text" 
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Filter yield by Chip ID, Corner, or Wafer ID..." 
                />
              </div>
            </div>

            {/* Datagrid */}
            <div className="table-wrapper">
              <table className="yield-table">
                <thead>
                  <tr>
                    <th>Chip ID</th>
                    <th>Wafer ID</th>
                    <th>Revision</th>
                    <th>Process Corner</th>
                    <th>Static Leakage Power (W)</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredYield.map((row, idx) => {
                    const isOutlier = yieldStats && row.Static_Leakage_Power > yieldStats.threshold3s;
                    const isHardViolator = spec && row.Static_Leakage_Power > spec.P_leakage_max;
                    const hasIssue = isOutlier || isHardViolator;
                    
                    return (
                      <tr 
                        key={idx} 
                        className={`${hasIssue ? 'violator' : ''} ${activeChip === row.Chip_ID ? 'active-row' : ''}`}
                        onClick={() => {
                          setActiveChip(row.Chip_ID);
                          setActiveTab('telemetry');
                        }}
                        title="Click to inspect time-series logs"
                      >
                        <td className="mono font-bold">{row.Chip_ID}</td>
                        <td className="mono">{row.Wafer_ID}</td>
                        <td className="mono">{row.Silicon_Revision}</td>
                        <td>{row.Corner}</td>
                        <td className="mono font-bold text-right">{row.Static_Leakage_Power} W</td>
                        <td>
                          {isHardViolator ? (
                            <span className="status-pill fail">Spec Breach</span>
                          ) : isOutlier ? (
                            <span className="status-pill warning">3σ Outlier</span>
                          ) : (
                            <span className="status-pill pass">Normal</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tab 4: Stress Telemetry Logs */}
        {activeTab === 'telemetry' && (
          <div className="tab-pane telemetry-pane animate-fade">
            <div className="telemetry-toolbar">
              <div className="selector-group">
                <span>Inspect Chip Sensor Logs:</span>
                <select 
                  value={activeChip} 
                  onChange={(e) => setActiveChip(e.target.value)}
                  className="chip-select"
                >
                  <option value="CX8_002">CX8_002 (Fast-Fast Corner Outlier)</option>
                  <option value="CX8_001">CX8_001 (Typical Corner Normal)</option>
                </select>
              </div>

              {activeChip === 'CX8_002' && (
                <div className="status-bar alert alert-danger">
                  <AlertOctagon size={16} />
                  <span>Silicon Failure: CX8_002 exceeded safe operating temperature (T_jmax: 105.0°C) during stress testing.</span>
                </div>
              )}
            </div>

            {/* Recharts Container */}
            <div className="chart-wrapper glass-card">
              {telemetry.length > 0 ? (
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={telemetry} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                    <XAxis 
                      dataKey="Timestamp" 
                      stroke="#666" 
                      tickFormatter={(tick) => `+${tick - 1710500000}s`} 
                      label={{ value: 'Stress Run Time (seconds)', position: 'insideBottom', offset: -5, fill: '#666' }}
                    />
                    <YAxis 
                      yAxisId="left"
                      stroke="#666" 
                      label={{ value: 'Junction Temp (°C) / Power (W)', angle: -90, position: 'insideLeft', fill: '#666' }}
                    />
                    <YAxis 
                      yAxisId="right"
                      orientation="right"
                      stroke="#666" 
                      domain={[0.78, 0.84]}
                      tickFormatter={(tick) => `${tick}V`}
                      label={{ value: 'Core Voltage (V)', angle: 90, position: 'insideRight', fill: '#666' }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend verticalAlign="top" height={36} />
                    
                    {/* Safe bounds references */}
                    {activeTab === 'telemetry' && spec && (
                      <>
                        <ReferenceLine yAxisId="left" y={spec.T_jmax} stroke="var(--color-error)" strokeDasharray="5 5" label={{ value: 'T_jmax: 105°C', fill: 'var(--color-error)', position: 'insideBottomRight' }} />
                        <ReferenceLine yAxisId="left" y={spec.Throttling_Trigger} stroke="var(--color-warning)" strokeDasharray="3 3" label={{ value: 'Throttling: 98°C', fill: 'var(--color-warning)', position: 'insideBottomRight' }} />
                      </>
                    )}
                    
                    <Line 
                      yAxisId="left"
                      type="monotone" 
                      dataKey="Temperature_C" 
                      name="Junction Temp" 
                      stroke="var(--color-error)" 
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 6 }}
                    />
                    <Line 
                      yAxisId="left"
                      type="monotone" 
                      dataKey="Dynamic_Power_W" 
                      name="Dynamic Power" 
                      stroke="var(--brand-green)" 
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line 
                      yAxisId="right"
                      type="step" 
                      dataKey="Core_Voltage_V" 
                      name="Core Voltage" 
                      stroke="var(--color-info)" 
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="empty-chart text-muted">
                  <Activity size={32} style={{ marginBottom: '10px' }} />
                  <span>Loading telemetry dataset...</span>
                </div>
              )}
            </div>

            {/* Raw telemetry table below chart */}
            {telemetry.length > 0 && (
              <div className="telemetry-table-wrapper">
                <h4>Raw Sensor Readings for {activeChip}</h4>
                <div className="table-wrapper mini">
                  <table className="yield-table mini">
                    <thead>
                      <tr>
                        <th>Offset Time</th>
                        <th>Voltage (V)</th>
                        <th>Junction Temp (°C)</th>
                        <th>Dynamic Power (W)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {telemetry.slice(0, 10).map((row, idx) => (
                        <tr key={idx} className={row.Temperature_C > (spec?.T_jmax || 105.0) ? 'violator' : ''}>
                          <td>+{row.Timestamp - 1710500000}s</td>
                          <td className="mono">{row.Core_Voltage_V} V</td>
                          <td className={`mono font-bold ${row.Temperature_C > (spec?.T_jmax || 105.0) ? 'text-red' : ''}`}>
                            {row.Temperature_C}°C
                          </td>
                          <td className="mono">{row.Dynamic_Power_W} W</td>
                        </tr>
                      ))}
                      {telemetry.length > 10 && (
                        <tr>
                          <td colSpan="4" className="text-muted text-center" style={{ fontSize: '0.8rem', padding: '6px' }}>
                            Showing first 10 logs. Total logs loaded: {telemetry.length} timestamps.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Embedded CSS */}
      <style>{`
        .data-browser {
          display: grid;
          grid-template-rows: 48px 1fr;
          height: 100%;
          overflow: hidden;
        }
        .tabs-header {
          display: flex;
          background-color: var(--bg-secondary);
          border-bottom: 1px solid var(--border-color);
          padding: 0 10px;
          gap: 4px;
        }
        .tab-btn {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 0 16px;
          height: 48px;
          color: var(--text-secondary);
          font-family: var(--font-display);
          font-weight: 500;
          font-size: 0.85rem;
          border-bottom: 2px solid transparent;
        }
        .tab-btn:hover {
          color: var(--text-primary);
          background-color: rgba(255, 255, 255, 0.02);
        }
        .tab-btn.active {
          color: var(--brand-green);
          border-bottom-color: var(--brand-green);
          background-color: rgba(118, 185, 0, 0.03);
          font-weight: 600;
        }
        .tab-content-container {
          flex: 1;
          overflow: hidden;
          background-color: var(--bg-primary);
        }
        .tab-pane {
          height: 100%;
          overflow-y: auto;
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .center-pane {
          justify-content: center;
          align-items: center;
        }
        .glow-icon {
          filter: drop-shadow(0 0 12px var(--brand-green));
        }
        
        /* Specs Pane Styling */
        .spec-card {
          padding: 30px !important;
        }
        .spec-title {
          font-size: 1.3rem;
          color: var(--text-primary);
          margin-bottom: 20px;
        }
        .spec-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 20px;
          margin-bottom: 30px;
        }
        .spec-item {
          background-color: rgba(0, 0, 0, 0.2);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: 16px;
        }
        .spec-item span {
          display: block;
          font-size: 0.78rem;
          color: var(--text-secondary);
          margin-bottom: 6px;
        }
        .spec-item strong {
          display: block;
          font-size: 1.4rem;
          font-family: var(--font-display);
          color: var(--text-primary);
          margin-bottom: 8px;
        }
        .text-red { color: var(--color-error); }
        .text-orange { color: var(--color-warning); }
        .spec-desc {
          font-size: 0.75rem;
          color: var(--text-muted);
          line-height: 1.3;
        }
        .spec-raw h4 {
          font-size: 0.85rem;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }
        .spec-raw pre {
          background-color: #050608;
          border: 1px solid var(--border-color);
          border-radius: 6px;
          padding: 16px;
          font-family: var(--font-mono);
          font-size: 0.8rem;
          white-space: pre-wrap;
          line-height: 1.5;
        }

        /* Yield Pane Styling */
        .yield-summary-panel {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
          padding: 14px 20px !important;
        }
        .yield-summary-panel span {
          font-size: 0.75rem;
          color: var(--text-secondary);
          display: block;
          margin-bottom: 2px;
        }
        .yield-summary-panel strong {
          font-size: 1.0rem;
          color: var(--text-primary);
        }
        .yield-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .search-bar {
          display: flex;
          align-items: center;
          background-color: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          padding: 0 12px;
          width: 320px;
          gap: 8px;
          height: 38px;
        }
        .search-bar input {
          background: none;
          border: none;
          color: var(--text-primary);
          outline: none;
          font-size: 0.85rem;
          flex: 1;
        }
        .table-wrapper {
          border: 1px solid var(--border-color);
          border-radius: 8px;
          background-color: var(--bg-secondary);
          overflow-x: auto;
          flex: 1;
        }
        .table-wrapper.mini {
          flex: none;
          max-height: 200px;
        }
        .yield-table {
          width: 100%;
          border-collapse: collapse;
          text-align: left;
          font-size: 0.85rem;
        }
        .yield-table th {
          background-color: rgba(255, 255, 255, 0.02);
          border-bottom: 1px solid var(--border-color);
          padding: 12px 16px;
          font-weight: 600;
          color: var(--text-secondary);
          font-family: var(--font-display);
        }
        .yield-table td {
          padding: 12px 16px;
          border-bottom: 1px solid var(--border-color);
          color: var(--text-primary);
        }
        .yield-table tbody tr {
          cursor: pointer;
          transition: background-color 0.15s;
        }
        .yield-table tbody tr:hover {
          background-color: rgba(255, 255, 255, 0.02);
        }
        .yield-table tbody tr.active-row {
          background-color: rgba(118, 185, 0, 0.05);
        }
        .yield-table tbody tr.violator {
          background-color: rgba(239, 68, 68, 0.03);
        }
        .yield-table tbody tr.violator:hover {
          background-color: rgba(239, 68, 68, 0.06);
        }
        .yield-table tbody tr.active-row.violator {
          background-color: rgba(239, 68, 68, 0.08);
        }
        .yield-table th.text-right, .yield-table td.text-right {
          text-align: right;
        }
        .mono {
          font-family: var(--font-mono);
          font-size: 0.8rem;
        }
        .font-bold {
          font-weight: 600;
        }
        .status-pill {
          font-size: 0.72rem;
          padding: 2px 8px;
          border-radius: 20px;
          font-weight: 600;
          display: inline-block;
        }
        .status-pill.pass {
          background-color: rgba(16, 185, 129, 0.15);
          color: rgb(16, 185, 129);
          border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .status-pill.warning {
          background-color: rgba(245, 158, 11, 0.15);
          color: rgb(245, 158, 11);
          border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .status-pill.fail {
          background-color: rgba(239, 68, 68, 0.15);
          color: rgb(239, 68, 68);
          border: 1px solid rgba(239, 68, 68, 0.3);
        }

        /* Telemetry Pane Styling */
        .telemetry-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 12px;
        }
        .selector-group {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.9rem;
        }
        .chip-select {
          background-color: var(--bg-secondary);
          border: 1px solid var(--border-color);
          color: var(--text-primary);
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 0.85rem;
          outline: none;
          cursor: pointer;
        }
        .alert {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 0.8rem;
          font-weight: 500;
        }
        .alert-danger {
          background-color: var(--color-error-glow);
          color: var(--color-error);
          border: 1px solid var(--color-error);
        }
        .chart-wrapper {
          padding: 20px !important;
        }
        .empty-chart {
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          height: 320px;
          border: 1px dashed var(--border-color);
          border-radius: 6px;
        }
        .chart-tooltip {
          padding: 10px 12px !important;
          border-left: 3px solid var(--brand-green) !important;
        }
        .tooltip-time {
          font-size: 0.78rem;
          color: var(--text-muted);
          margin-bottom: 6px;
          font-weight: 600;
        }
        .telemetry-table-wrapper h4 {
          font-size: 0.9rem;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }
        
        /* Fade In Effect */
        .animate-fade {
          animation: slideIn 0.25s ease-out;
        }
      `}</style>
    </div>
  )
}

export default DataBrowser
