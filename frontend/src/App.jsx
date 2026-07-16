import React, { useState, useEffect } from 'react'
import { Terminal, Database, FileText, Cpu, Activity, Send, MessageSquare } from 'lucide-react'
import ChatWindow from './components/ChatWindow.jsx'
import DataBrowser from './components/DataBrowser.jsx'
import TraceVisualizer from './components/TraceVisualizer.jsx'

function App() {
  const [currentTab, setCurrentTab] = useState('chat') // 'chat', 'specs', 'yield', 'telemetry'
  const [activeChip, setActiveChip] = useState('CX8_002')
  
  // Data Caches
  const [spec, setSpec] = useState(null)
  const [yieldData, setYieldData] = useState([])
  const [telemetry, setTelemetry] = useState([])
  
  // Chat & Trace states
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: (
        "Hello! I am your **ASIC Copilot**.\n\n" +
        "I can help you analyze silicon bring-up yield logs and time-series telemetry data across process corners.\n\n" +
        "Click on any sample question below to automatically load it:"
      ),
      suggestions: [
        "Analyze our latest PVT run for Revision B0 and tell me if any chips violated our specifications",
        "Show me wafer yield static leakage and list FF corner outliers",
        "Compare sensor logs of chip CX8_002 and tell me if it triggered thermal throttling"
      ],
      anomalies: null
    }
  ])
  const [traceLogs, setTraceLogs] = useState([])
  const [isLoading, setIsLoading] = useState(false)

  // Fetch baseline databases on mount
  useEffect(() => {
    fetchSpec()
    fetchYield()
  }, [])

  // Fetch telemetry when activeChip changes
  useEffect(() => {
    if (activeChip) {
      fetchTelemetry(activeChip)
    }
  }, [activeChip])

  const fetchSpec = async () => {
    try {
      const res = await fetch('/api/data/spec')
      if (res.ok) {
        const data = await res.json()
        setSpec(data)
      }
    } catch (e) {
      console.error('Failed to fetch specs:', e)
    }
  }

  const fetchYield = async () => {
    try {
      const res = await fetch('/api/data/yield')
      if (res.ok) {
        const data = await res.json()
        setYieldData(data)
      }
    } catch (e) {
      console.error('Failed to fetch yield:', e)
    }
  }

  const fetchTelemetry = async (chipId) => {
    try {
      const res = await fetch(`/api/data/telemetry/${chipId}`)
      if (res.ok) {
        const data = await res.json()
        setTelemetry(data)
      } else {
        setTelemetry([])
      }
    } catch (e) {
      console.error(`Failed to fetch telemetry for ${chipId}:`, e)
      setTelemetry([])
    }
  }

  const handleSendMessage = async (text) => {
    if (!text.trim()) return
    
    // Add user message
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setIsLoading(true)
    setTraceLogs([]) // Reset traces for new query

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      })

      if (res.ok) {
        const data = await res.json()
        
        // Populate agent trace logs
        if (data.trace_logs) {
          setTraceLogs(data.trace_logs)
        }

        // Add assistant message with markdown report and anomalies list
        const assistantMsg = {
          role: 'assistant',
          content: data.final_markdown_report || "Failed to generate text report.",
          anomalies: data.flaged_anomalies ? data.flaged_anomalies[0] : null
        }
        setMessages(prev => [...prev, assistantMsg])
        
        // Auto-switch tabs based on router targets if specified
        if (data.required_sources && data.required_sources.includes('telemetry')) {
          // Check if a chip was targeted
          const queryLower = text.toLowerCase()
          let target = 'CX8_002'
          if (queryLower.includes('cx8_001')) target = 'CX8_001'
          else if (queryLower.includes('cx8_003')) target = 'CX8_003'
          
          setActiveChip(target)
        }
      } else {
        const err = await res.json()
        let errorContent
        if (res.status === 429 && err.detail?.type === 'rate_limit') {
          const secs = err.detail.retry_after_seconds || 30
          const mins = Math.ceil(secs / 60)
          errorContent = (
            `⏳ **Rate limit reached (free API tier)**\n\n` +
            `The Google Gemini API has a quota of 20 requests/day on the free tier. ` +
            `You've reached today's limit.\n\n` +
            `**Please try again in ~${secs < 60 ? `${secs} seconds` : `${mins} minute${mins > 1 ? 's' : ''}`}.** ` +
            `You can also check your current usage at [ai.dev/rate-limit](https://ai.dev/rate-limit).`
          )
        } else {
          errorContent = `⚠️ **Error executing agent workflow:** ${err.detail?.message || err.detail || 'Unknown error'}`
        }
        setMessages(prev => [...prev, { role: 'assistant', content: errorContent }])
      }
    } catch (e) {
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `⚠️ **Network failure connecting to agent API:** ${e.message}` 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="logo-section">
          <Cpu size={24} className="text-green" />
          <h1><span className="logo-accent">ASIC Copilot</span></h1>
        </div>
        <div className="status-badge">
          <div className="status-dot"></div>
          <span>Silicon Rev B0 Active</span>
        </div>
      </header>

      {/* Main Workspace with Sidebar and content area */}
      <main className="app-workspace">
        {/* Left Side: Navigation Sidebar (icons only) */}
        <nav className="app-sidebar">
          <div className="sidebar-nav-items">
            <button 
              className={`nav-icon-btn ${currentTab === 'chat' ? 'active' : ''}`}
              onClick={() => setCurrentTab('chat')}
              data-tooltip="Interactive Chat"
            >
              <MessageSquare size={20} />
            </button>
            <button 
              className={`nav-icon-btn ${currentTab === 'specs' ? 'active' : ''}`}
              onClick={() => setCurrentTab('specs')}
              data-tooltip="Design Specifications"
            >
              <FileText size={20} />
            </button>
            <button 
              className={`nav-icon-btn ${currentTab === 'yield' ? 'active' : ''}`}
              onClick={() => setCurrentTab('yield')}
              data-tooltip="Wafer Yield Data"
            >
              <Database size={20} />
            </button>
            <button 
              className={`nav-icon-btn ${currentTab === 'telemetry' ? 'active' : ''}`}
              onClick={() => setCurrentTab('telemetry')}
              data-tooltip="Stress Telemetry Logs"
            >
              <Activity size={20} />
            </button>
          </div>
        </nav>

        {/* Dynamic Content Panel */}
        <div className="workspace-content">
          {/* Chat Window Panel */}
          {currentTab === 'chat' && (
            <section className="sidebar-container full-width">
              <div style={{ display: 'grid', gridTemplateRows: '1fr auto', height: '100%', overflow: 'hidden' }}>
                <ChatWindow 
                  messages={messages} 
                  isLoading={isLoading} 
                  onSend={handleSendMessage} 
                  onSelectChip={(chipId) => {
                    setActiveChip(chipId)
                    setCurrentTab('telemetry')
                  }}
                />
                {traceLogs.length > 0 && (
                  <TraceVisualizer logs={traceLogs} />
                )}
              </div>
            </section>
          )}

          {/* Data Dashboard Panel */}
          {currentTab !== 'chat' && (
            <section className="main-content full-width">
              <DataBrowser 
                activeTab={currentTab} 
                setActiveTab={setCurrentTab}
                spec={spec}
                yieldData={yieldData}
                telemetry={telemetry}
                activeChip={activeChip}
                setActiveChip={setActiveChip}
              />
            </section>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
