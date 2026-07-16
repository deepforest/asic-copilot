import React, { useState, useRef, useEffect } from 'react'
import { Send, User, Cpu, AlertTriangle } from 'lucide-react'

// Unified inline renderer: handles **bold**, *italic*, and CX8_xxx chip buttons in a single pass
const renderInline = (text, onSelectChip) => {
  if (!text) return null
  // Tokenize by any inline patterns we care about
  const tokens = text.split(/(\*\*.*?\*\*|\*[^*]+?\*|CX8_\d{3})/g)
  return tokens.map((tok, i) => {
    if (tok.startsWith('**') && tok.endsWith('**') && tok.length > 4) {
      return <strong key={i}>{tok.slice(2, -2)}</strong>
    }
    if (tok.startsWith('*') && tok.endsWith('*') && tok.length > 2) {
      return <em key={i}>{tok.slice(1, -1)}</em>
    }
    if (tok.match(/^CX8_\d{3}$/)) {
      return (
        <button
          key={i}
          className="chip-mention-btn"
          onClick={() => onSelectChip(tok)}
          title={`Click to inspect telemetry for ${tok}`}
        >
          {tok}
        </button>
      )
    }
    return tok
  })
}

const renderMessageContent = (text, onSelectChip) => {
  if (!text) return ''

  const lines = text.split('\n')
  const blocks = []
  let currentTable = null

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // Table lines
    if (trimmed.startsWith('|')) {
      // Skip separator rows like | :--- | --- |
      if (trimmed.match(/^\|[\s\-:\|]+$/) || trimmed.includes(':---')) {
        continue
      }
      const cells = trimmed.split('|')
        .map(c => c.trim())
        .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)

      if (!currentTable) {
        currentTable = { headers: cells, rows: [] }
      } else {
        currentTable.rows.push(cells)
      }
      continue
    }

    // Flush any pending table
    if (currentTable) {
      blocks.push({ type: 'table', content: currentTable })
      currentTable = null
    }

    if (trimmed === '') continue
    if (trimmed === '---') { blocks.push({ type: 'hr' }); continue }
    if (trimmed.startsWith('### ')) { blocks.push({ type: 'h3', text: trimmed.substring(4) }); continue }
    if (trimmed.startsWith('## '))  { blocks.push({ type: 'h2', text: trimmed.substring(3) }); continue }
    if (trimmed.startsWith('# '))   { blocks.push({ type: 'h1', text: trimmed.substring(2) }); continue }
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      blocks.push({ type: 'li', text: trimmed.substring(2) }); continue
    }
    // Numbered list items like "1. " "2. "
    if (trimmed.match(/^\d+\.\s/)) {
      blocks.push({ type: 'li', text: trimmed.replace(/^\d+\.\s/, '') }); continue
    }
    blocks.push({ type: 'p', text: trimmed })
  }

  if (currentTable) blocks.push({ type: 'table', content: currentTable })

  return blocks.map((block, bIdx) => {
    if (block.type === 'h1') return <h1 key={bIdx} className="md-h1">{renderInline(block.text, onSelectChip)}</h1>
    if (block.type === 'h2') return <h2 key={bIdx} className="md-h2">{renderInline(block.text, onSelectChip)}</h2>
    if (block.type === 'h3') return <h3 key={bIdx} className="md-h3">{renderInline(block.text, onSelectChip)}</h3>
    if (block.type === 'li') return <li key={bIdx} className="md-li">{renderInline(block.text, onSelectChip)}</li>
    if (block.type === 'hr') return <hr key={bIdx} style={{ margin: '16px 0', border: 'none', borderBottom: '1px solid var(--border-color)' }} />
    if (block.type === 'p')  return <p key={bIdx} className="md-p">{renderInline(block.text, onSelectChip)}</p>
    if (block.type === 'table') {
      return (
        <div key={bIdx} className="table-responsive" style={{ margin: '14px 0', overflowX: 'auto' }}>
          <table className="md-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem', border: '1px solid var(--border-color)' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.04)', borderBottom: '1px solid var(--border-color)' }}>
                {block.content.headers.map((h, hIdx) => (
                  <th key={hIdx} style={{ padding: '10px 12px', textAlign: 'left', fontWeight: '600' }}>
                    {renderInline(h, onSelectChip)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.content.rows.map((row, rIdx) => (
                <tr key={rIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx} style={{ padding: '10px 12px', color: 'var(--text-secondary)' }}>
                      {renderInline(cell, onSelectChip)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )
    }
    return null
  })
}

// parseBolds kept for backwards compatibility (welcome message uses it via suggestions rendering)
const parseBolds = (text) => {
  const parts = text.split(/(\*\*.*?\*\*)/g)
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.substring(2, part.length - 2)}</strong>
    }
    return part
  })
}

function ChatWindow({ messages, isLoading, onSend, onSelectChip }) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLoading])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim()) return
    onSend(input)
    setInput('')
  }

  return (
    <div className="chat-window">
      {/* Messages Scroll Area */}
      <div className="messages-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message-bubble ${msg.role}`}>
            <div className="avatar-container">
              {msg.role === 'user' ? (
                <div className="avatar user"><User size={16} /></div>
              ) : (
                <div className="avatar assistant"><Cpu size={16} /></div>
              )}
            </div>
            
            <div className="message-content">
              <div className="message-text">
                {renderMessageContent(msg.content, onSelectChip)}
              </div>
              
              {/* Structured Anomaly Pydantic Output Box */}
              {msg.anomalies && (
                <div className="anomaly-box glass-card glow-card">
                  <div className="anomaly-header">
                    <AlertTriangle size={16} style={{ color: 'var(--color-warning)' }} />
                    <h4>ASIC Anomaly Payload Detected</h4>
                  </div>
                  <div className="anomaly-payload-grid">
                    <div>
                      <span>Flagged Chips:</span>
                      <strong>{msg.anomalies.anomalous_chip_ids?.join(', ') || 'None'}</strong>
                    </div>
                    <div>
                      <span>Violation Category:</span>
                      <strong className="violation-badge">{msg.anomalies.violation_type}</strong>
                    </div>
                    <div>
                      <span>Confidence Score:</span>
                      <strong>{(msg.anomalies.confidence_score * 100).toFixed(0)}%</strong>
                    </div>
                  </div>
                  <div className="anomaly-payload-explanation">
                    <span>Root Cause Explanation:</span>
                    <p>{msg.anomalies.root_cause_explanation}</p>
                  </div>
                </div>
              )}
              {msg.suggestions && (
                <div className="suggestions-list" style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {msg.suggestions.map((sugg, sIdx) => (
                    <button
                      key={sIdx}
                      className="suggestion-link"
                      type="button"
                      onClick={() => setInput(sugg)}
                      style={{
                        textAlign: 'left',
                        padding: '10px 14px',
                        borderRadius: '8px',
                        background: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid var(--border-color)',
                        color: 'var(--brand-green)',
                        fontSize: '0.85rem',
                        lineHeight: '1.4',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                      }}
                      onMouseOver={(e) => {
                        e.currentTarget.style.background = 'rgba(118, 185, 0, 0.08)';
                        e.currentTarget.style.borderColor = 'rgba(118, 185, 0, 0.2)';
                      }}
                      onMouseOut={(e) => {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                        e.currentTarget.style.borderColor = 'var(--border-color)';
                      }}
                    >
                      💡 "{sugg}"
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message-bubble assistant">
            <div className="avatar-container">
              <div className="avatar assistant"><Cpu size={16} /></div>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span className="dot"></span>
                <span className="dot"></span>
                <span className="dot"></span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Tray */}
      <form onSubmit={handleSubmit} className="input-tray">
        <input 
          type="text" 
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask ASIC Copilot about PVT parameters, leakage power, or temperature limits..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading || !input.trim()}>
          <Send size={18} />
        </button>
      </form>

      {/* Embedded CSS for Chat-specific components */}
      <style>{`
        .chat-window {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0; /* critical: allows flex children to shrink below content size */
          overflow: hidden;
        }
        .messages-container {
          flex: 1;
          min-height: 0; /* allows scroll container to shrink properly */
          overflow-y: auto;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .message-bubble {
          display: flex;
          gap: 12px;
          animation: slideIn 0.25s ease-out;
        }
        .message-bubble.user {
          flex-direction: row-reverse;
        }
        .avatar {
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .avatar.assistant {
          background-color: var(--brand-green-glow);
          border: 1px solid var(--brand-green);
          color: var(--brand-green);
        }
        .avatar.user {
          background-color: rgba(255, 255, 255, 0.05);
          border: 1px solid var(--border-color);
          color: var(--text-primary);
        }
        .message-content {
          max-width: 80%;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .message-text {
          padding: 12px 16px;
          border-radius: 12px;
          line-height: 1.5;
        }
        .assistant .message-text {
          background-color: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          color: var(--text-primary);
        }
        .user .message-text {
          background-color: var(--brand-green);
          color: var(--bg-primary);
          font-weight: 500;
        }
        .chip-mention-btn {
          background-color: rgba(118, 185, 0, 0.12);
          border: 1px solid rgba(118, 185, 0, 0.4);
          color: var(--brand-green);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.85rem;
          font-family: var(--font-mono);
          font-weight: 600;
          display: inline-block;
          margin: 0 4px;
          transition: all 0.2s;
        }
        .chip-mention-btn:hover {
          background-color: var(--brand-green);
          color: var(--bg-primary);
          box-shadow: 0 0 8px var(--brand-green);
        }
        .input-tray {
          display: flex;
          flex-shrink: 0; /* never shrink — always pinned to bottom */
          padding: 16px;
          border-top: 1px solid var(--border-color);
          background-color: var(--bg-secondary);
          gap: 10px;
        }
        .input-tray input {
          flex: 1;
          background-color: var(--bg-input);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: 12px 16px;
          color: var(--text-primary);
          font-family: var(--font-sans);
          font-size: 0.9rem;
          outline: none;
          transition: all 0.2s;
        }
        .input-tray input:focus {
          border-color: var(--brand-green);
          box-shadow: 0 0 10px rgba(118, 185, 0, 0.1);
        }
        .input-tray button {
          width: 44px;
          height: 44px;
          border-radius: 8px;
          background-color: var(--brand-green);
          color: var(--bg-primary);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .input-tray button:hover:not(:disabled) {
          background-color: var(--brand-green-hover);
          box-shadow: 0 0 10px var(--brand-green);
        }
        .input-tray button:disabled {
          background-color: rgba(255, 255, 255, 0.04);
          color: var(--text-muted);
          border: 1px solid var(--border-color);
          cursor: not-allowed;
        }
        /* Structured Output Anomaly Card */
        .anomaly-box {
          border-left: 4px solid var(--color-warning) !important;
          animation: slideIn 0.3s ease-out;
        }
        .anomaly-header {
          display: flex;
          align-items: center;
          gap: 8px;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 8px;
          margin-bottom: 10px;
        }
        .anomaly-header h4 {
          font-size: 0.9rem;
          font-weight: 600;
          color: var(--text-primary);
        }
        .anomaly-payload-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
          font-size: 0.8rem;
          margin-bottom: 10px;
        }
        .anomaly-payload-grid span {
          color: var(--text-secondary);
          display: block;
          margin-bottom: 2px;
        }
        .anomaly-payload-grid strong {
          color: var(--text-primary);
          font-size: 0.85rem;
        }
        .violation-badge {
          background-color: var(--color-error-glow);
          color: var(--color-error) !important;
          border: 1px solid var(--color-error);
          padding: 1px 6px;
          border-radius: 4px;
          font-size: 0.75rem;
          display: inline-block;
        }
        .anomaly-payload-explanation span {
          font-size: 0.8rem;
          color: var(--text-secondary);
          display: block;
          margin-bottom: 4px;
        }
        .anomaly-payload-explanation p {
          font-size: 0.82rem;
          line-height: 1.4;
          color: var(--text-primary);
          background-color: rgba(0, 0, 0, 0.15);
          padding: 8px;
          border-radius: 6px;
          border: 1px solid var(--border-color);
        }
        /* Basic Markdown Styles */
        .md-h1 { font-size: 1.25rem; font-weight: 700; margin: 12px 0 6px; color: var(--brand-green); font-family: var(--font-display); }
        .md-h2 { font-size: 1.15rem; font-weight: 600; margin: 10px 0 6px; color: var(--text-primary); border-bottom: 1px solid var(--border-color); padding-bottom: 2px; }
        .md-h3 { font-size: 1.0rem; font-weight: 600; margin: 8px 0 4px; color: var(--text-primary); }
        .md-p { margin-bottom: 8px; }
        .md-li { margin-left: 20px; list-style-type: square; margin-bottom: 4px; }
        /* Typing indicator dots */
        .typing-indicator {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 12px 16px;
          border-radius: 12px;
          background-color: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
        }
        .typing-indicator .dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background-color: var(--text-muted);
          animation: bounce 1.4s infinite ease-in-out both;
        }
        .typing-indicator .dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-indicator .dot:nth-child(2) { animation-delay: -0.16s; }
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1.0); }
        }
      `}</style>
    </div>
  )
}

export default ChatWindow
