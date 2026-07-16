import React, { useState, useEffect, useRef } from 'react'
import { Terminal, ChevronDown, ChevronUp } from 'lucide-react'

function TraceVisualizer({ logs }) {
  const [isOpen, setIsOpen] = useState(true)
  const logsEndRef = useRef(null)

  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    if (isOpen) {
      scrollToBottom()
    }
  }, [logs, isOpen])

  const formatLogLine = (line) => {
    if (line.includes('[Analytics Router]')) {
      return <span className="trace-router">{line}</span>
    }
    if (line.includes('[Data Collector]')) {
      return <span className="trace-collector">{line}</span>
    }
    if (line.includes('WARNING') || line.includes('outlier') || line.includes('exception')) {
      return <span className="trace-warning">{line}</span>
    }
    if (line.includes('ERROR')) {
      return <span className="trace-error">{line}</span>
    }
    if (line.includes('[Correlation Agent]')) {
      return <span className="trace-correlation">{line}</span>
    }
    if (line.includes('[Insights Generator]')) {
      return <span className="trace-generator">{line}</span>
    }
    return <span>{line}</span>
  }

  return (
    <div className={`trace-visualizer ${isOpen ? 'expanded' : 'collapsed'}`}>
      {/* Header */}
      <div className="trace-header" onClick={() => setIsOpen(!isOpen)}>
        <div className="trace-title">
          <Terminal size={14} className="text-green" />
          <span>Execution Traces ({logs.length} steps)</span>
        </div>
        <button>{isOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}</button>
      </div>

      {/* Terminal Output */}
      {isOpen && (
        <div className="trace-console">
          {logs.map((log, idx) => (
            <div key={idx} className="trace-line">
              <span className="trace-prompt">&gt;</span>
              <pre className="trace-text">{formatLogLine(log)}</pre>
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      )}

      {/* Embedded CSS */}
      <style>{`
        .trace-visualizer {
          border-top: 1px solid var(--border-color);
          background-color: #0b0c10;
          display: flex;
          flex-direction: column;
          max-height: 240px;
          transition: height 0.3s;
        }
        .trace-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 10px 16px;
          background-color: #0f1015;
          cursor: pointer;
          user-select: none;
        }
        .trace-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-family: var(--font-display);
          font-size: 0.8rem;
          font-weight: 600;
          color: var(--text-primary);
        }
        .trace-header button {
          color: var(--text-muted);
        }
        .trace-header:hover button {
          color: var(--text-primary);
        }
        .trace-console {
          flex: 1;
          overflow-y: auto;
          padding: 12px 16px;
          display: flex;
          flex-direction: column;
          gap: 6px;
          font-family: var(--font-mono);
          font-size: 0.78rem;
          line-height: 1.4;
          background-color: #050608;
        }
        .trace-line {
          display: flex;
          gap: 6px;
          align-items: flex-start;
        }
        .trace-prompt {
          color: var(--brand-green);
          font-weight: 700;
          user-select: none;
        }
        .trace-text {
          white-space: pre-wrap;
          word-break: break-all;
          margin: 0;
          font-family: inherit;
        }
        .trace-router { color: #60a5fa; } /* Blue */
        .trace-collector { color: #a78bfa; } /* Purple */
        .trace-correlation { color: #f472b6; } /* Pink */
        .trace-generator { color: #fb7185; } /* Rose */
        .trace-warning { color: var(--color-warning); font-weight: 500; }
        .trace-error { color: var(--color-error); font-weight: 600; }
      `}</style>
    </div>
  )
}

export default TraceVisualizer
