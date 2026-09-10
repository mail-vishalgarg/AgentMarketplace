import React, { useState, useEffect } from 'react'
import api from '../api/client'

export default function MCPServersPage() {
  const [servers, setServers] = useState([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [errorBanner, setErrorBanner] = useState(null)
  const [saving, setSaving] = useState(false)

  // Expanded cards state for '+ 2 more'
  const [expandedCards, setExpandedCards] = useState({})

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    transport: 'http',
    url: '',
    auth_type: 'none',
    scope: 'shared',
    description: ''
  })

  const fetchServers = async () => {
    try {
      setLoading(true)
      const res = await api.get('/servers')
      setServers(res.data)
    } catch (err) {
      console.error('Failed to fetch servers:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchServers()
  }, [])

  const handleOpenModal = () => {
    setFormData({
      name: 'slack',
      transport: 'http',
      url: 'https://mcp.example.com/slack',
      auth_type: 'oauth',
      scope: 'tenant',
      description: 'Read channels and post messages to a workspace.'
    })
    setErrorBanner(null)
    setModalOpen(true)
  }

  const handleCloseModal = () => {
    setModalOpen(false)
    setErrorBanner(null)
  }

  // Quick Pre-fills
  const handlePrefill = (preset) => {
    setErrorBanner(null)
    if (preset === 'github') {
      setFormData({
        name: 'github',
        transport: 'http',
        url: 'http://localhost:8000/mock/github',
        auth_type: 'api_key',
        scope: 'shared',
        description: 'Issues, pull requests, commits and repository trees.'
      })
    } else if (preset === 'slack') {
      setFormData({
        name: 'slack',
        transport: 'http',
        url: 'http://localhost:8000/mock/slack',
        auth_type: 'oauth',
        scope: 'shared',
        description: 'Read channels and post messages to a workspace.'
      })
    } else if (preset === 'sqlite') {
      setFormData({
        name: 'sqlite',
        transport: 'stdio',
        url: 'http://localhost:8000/mock/sqlite',
        auth_type: 'none',
        scope: 'shared',
        description: 'Query a local SQLite database.'
      })
    } else if (preset === 'deadserver') {
      setFormData({
        name: 'dead-server',
        transport: 'http',
        url: 'http://localhost:8000/mock/deadserver',
        auth_type: 'api_key',
        scope: 'tenant',
        description: 'Unreachable dead endpoint test.'
      })
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setErrorBanner(null)
    setSaving(true)

    try {
      const payload = {
        name: formData.name.trim(),
        transport: formData.transport,
        url: formData.url.trim(),
        auth_type: formData.auth_type,
        scope: formData.scope,
        description: formData.description.trim() || undefined
      }

      await api.post('/servers', payload)
      // Success: close modal and refresh
      setSaving(false)
      setModalOpen(false)
      await fetchServers()
    } catch (err) {
      setSaving(false)
      // Display exact error message from backend
      const detail = err.response?.data?.detail || 'The server did not answer. Registration aborted.'
      setErrorBanner(detail.startsWith('✕') || detail.startsWith('×') ? detail : `✕ ${detail}`)
    }
  }

  const handleRefresh = async (serverId) => {
    try {
      await api.post(`/servers/${serverId}/refresh`)
      await fetchServers()
    } catch (err) {
      alert('Error refreshing server: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleDelete = async (serverId) => {
    if (!confirm('Are you sure you want to delete this MCP server?')) return
    try {
      await api.delete(`/servers/${serverId}`)
      await fetchServers()
    } catch (err) {
      alert('Error deleting server: ' + (err.response?.data?.detail || err.message))
    }
  }

  const handleToggleConnect = async (serverId) => {
    try {
      await api.post(`/servers/${serverId}/toggle-connect`)
      await fetchServers()
    } catch (err) {
      console.error('Error toggling connection:', err)
    }
  }

  const toggleExpand = (serverId) => {
    setExpandedCards(prev => ({ ...prev, [serverId]: !prev[serverId] }))
  }

  // Split servers into Shared and Private
  const sharedServers = servers.filter(s => s.scope === 'shared')
  const privateServers = servers.filter(s => s.scope === 'tenant')

  return (
    <div className="content-inner">
      {/* First-Time User Guide Banner */}
      <div className="instruction-box user-guide">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <span className="guide-badge">✦ FIRST-TIME USER GUIDE</span>
          <h4 style={{ margin: 0 }}>HOW TO USE THE MCP REGISTRY</h4>
        </div>
        <p className="guide-intro">
          MCP (Model Context Protocol) servers provide the real-world tools that your autonomous agents can invoke. Follow these steps to get started:
        </p>
        <ol>
          <li>
            <b>1. Explore Existing Servers:</b> Browse the pre-registered shared servers below (GitHub, Slack, SQLite, Filesystem, Git). Notice each server's live tool capabilities and health status.
          </li>
          <li>
            <b>2. Security &amp; Risk Badges:</b> Tools are automatically classified by risk:
            <span className="risk-tag read" style={{ margin: '0 5px' }}>read</span> (safe, executes automatically),
            <span className="risk-tag write" style={{ margin: '0 5px' }}>write</span> (creates or mutates state), and
            <span className="risk-tag destructive" style={{ margin: '0 5px' }}>destructive</span> (triggers a mandatory human approval pause before running).
          </li>
          <li>
            <b>3. Register a New Server:</b> Click the black <b>+ Register a server</b> button in the top right to open the registration popup. Select the transport (<code className="mono">http</code>, <code className="mono">sse</code>, or <code className="mono">stdio</code>) and enter the endpoint URL.
          </li>
          <li>
            <b>4. Dynamic Tool Introspection:</b> On save, Forge connects directly to the server and retrieves all available tools and parameters over JSON-RPC 2.0. You never enter tool schemas manually.
          </li>
          <li>
            <b>5. Failure Guard &amp; Health:</b> If a server is offline or fails to answer, registration is safely rejected—nothing is saved. Scheduled background checks monitor servers and flag offline ones as <span className="badge danger" style={{ margin: '0 4px' }}><span className="dot"></span>down</span>.
          </li>
          <li>
            <b>6. Next Step:</b> Once connected, visit <b>Connections</b> to store API keys and OAuth tokens, then click <b>✦ Build</b> to create an agent that uses these tools!
          </li>
        </ol>
      </div>

      {/* Page Title Row */}
      <div className="page-header-row">
        <div>
          <h1 className="page-title">MCP Registry</h1>
          <p className="page-subtitle">Tool servers your agents can use. Register one, connect once, reuse everywhere.</p>
        </div>
        <button className="btn primary" onClick={handleOpenModal}>
          + Register a server
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--muted)' }}>
          Loading MCP registry servers...
        </div>
      ) : (
        <>
          {/* Section: Shared servers */}
          <div className="section-header">
            <span className="section-title">Shared servers</span>
            <span className="section-count">{sharedServers.length}</span>
          </div>

          <div className="cards-grid">
            {sharedServers.map(s => renderServerCard(s, expandedCards, toggleExpand, handleRefresh, handleDelete, handleToggleConnect))}
          </div>

          {/* Section: Private to Northwind Labs */}
          <div className="section-header" style={{ marginTop: '36px' }}>
            <span className="section-title">Private to Northwind Labs</span>
            <span className="section-count">{privateServers.length}</span>
          </div>

          <div className="cards-grid">
            {privateServers.map(s => renderServerCard(s, expandedCards, toggleExpand, handleRefresh, handleDelete, handleToggleConnect))}
          </div>
        </>
      )}

      {/* ─── MODAL: REGISTER AN MCP SERVER ─── */}
      {modalOpen && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal modal-wide" onClick={e => e.stopPropagation()}>
            <div className="modal-header between">
              <div>
                <h2>Register an MCP server</h2>
                <p>Saved only after the platform successfully connects.</p>
              </div>
              <button
                type="button"
                className="btn-text"
                onClick={handleCloseModal}
                style={{ fontSize: '18px', border: 'none', background: 'none', cursor: 'pointer', color: 'var(--muted)' }}
              >
                ✕
              </button>
            </div>

            <div className="modal-body-split">
              {/* Left column: Registration Form */}
              <div className="modal-form-col">
                {/* Error Banner when connection fails */}
                {errorBanner && (
                  <div className="alert-banner">
                    {errorBanner}
                  </div>
                )}

                {/* Quick Pre-fills for Testing */}
                <div className="fld">
                  <label style={{ color: 'var(--muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                    Quick Pre-fills for Testing:
                  </label>
                  <div className="chip-row">
                    <span className="chip" onClick={() => handlePrefill('slack')}>+ Slack</span>
                    <span className="chip" onClick={() => handlePrefill('github')}>+ GitHub</span>
                    <span className="chip" onClick={() => handlePrefill('sqlite')}>+ SQLite</span>
                    <span className="chip dead" onClick={() => handlePrefill('deadserver')}>× Dead Server Test</span>
                  </div>
                </div>

                <form id="register-server-form" onSubmit={handleSubmit}>
                  {/* Name */}
                  <div className="fld">
                    <label>Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. slack"
                      value={formData.name}
                      onChange={e => setFormData({ ...formData, name: e.target.value })}
                    />
                  </div>

                  {/* Transport Dropdown */}
                  <div className="fld">
                    <label>Transport</label>
                    <select
                      value={formData.transport}
                      onChange={e => setFormData({ ...formData, transport: e.target.value })}
                    >
                      <option value="http">http</option>
                      <option value="sse">sse</option>
                      <option value="stdio">stdio</option>
                    </select>
                  </div>

                  {/* Endpoint */}
                  <div className="fld">
                    <label>Endpoint</label>
                    <input
                      type="text"
                      required
                      className="mono"
                      placeholder="https://mcp.example.com/slack"
                      value={formData.url}
                      onChange={e => setFormData({ ...formData, url: e.target.value })}
                    />
                  </div>

                  {/* Authentication Dropdown */}
                  <div className="fld">
                    <label>Authentication</label>
                    <select
                      value={formData.auth_type}
                      onChange={e => setFormData({ ...formData, auth_type: e.target.value })}
                    >
                      <option value="oauth">oauth</option>
                      <option value="api_key">api_key</option>
                      <option value="none">none</option>
                    </select>
                  </div>

                  {/* Visible to Dropdown */}
                  <div className="fld" style={{ marginBottom: '4px' }}>
                    <label>Visible to</label>
                    <select
                      value={formData.scope}
                      onChange={e => setFormData({ ...formData, scope: e.target.value })}
                    >
                      <option value="tenant">Just my workspace</option>
                      <option value="shared">Everyone (admin only)</option>
                    </select>
                  </div>

                  {/* Description (optional) */}
                  <div className="fld">
                    <label>Description (optional)</label>
                    <input
                      type="text"
                      placeholder="What tools does this server provide?"
                      value={formData.description}
                      onChange={e => setFormData({ ...formData, description: e.target.value })}
                    />
                  </div>
                </form>
              </div>

              {/* Right column: What happens on save card */}
              <div className="modal-info-col">
                <div className="save-card">
                  <div style={{ fontWeight: 650, fontSize: '13.5px', marginBottom: '10px', color: 'var(--ink)' }}>
                    What happens on save
                  </div>
                  <div className="check pass">
                    <span className="m">1</span>
                    <span>Open a connection to the endpoint</span>
                  </div>
                  <div className="check pass">
                    <span className="m">2</span>
                    <span>Ask it for its tool list</span>
                  </div>
                  <div className="check pass">
                    <span className="m">3</span>
                    <span>Mark each tool read, write or destructive</span>
                  </div>
                  <div className="check pass">
                    <span className="m">4</span>
                    <span>Store the list; mark the server healthy</span>
                  </div>
                  <div className="check fail">
                    <span className="m">✕</span>
                    <span style={{ color: 'var(--danger)', fontWeight: 600 }}>If it does not answer, nothing is saved</span>
                  </div>
                  <hr className="sep" style={{ margin: '14px 0' }} />
                  <div className="faint" style={{ fontSize: '12px', lineHeight: 1.5 }}>
                    A scheduled job re-checks every server and marks the dead ones. Agents that depend on a dead server show as degraded.
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer between">
              <div style={{ fontSize: '12px', color: 'var(--muted)' }}>
                {saving && <span>Connecting & introspecting tools...</span>}
              </div>
              <div className="row" style={{ gap: '10px' }}>
                <button type="button" className="btn sm" onClick={handleCloseModal} disabled={saving}>
                  Cancel
                </button>
                <button type="submit" form="register-server-form" className="btn primary sm" disabled={saving}>
                  {saving ? 'Connecting & saving...' : 'Connect & save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function renderServerCard(s, expandedCards, toggleExpand, onRefresh, onDelete, onToggleConnect) {
  const isExpanded = !!expandedCards[s.id]
  const displayedTools = isExpanded ? s.tools : s.tools.slice(0, 4)
  const remainingCount = s.tools.length - 4

  return (
    <div key={s.id} className="server-card">
      {/* Header */}
      <div className="server-card-header">
        <div className="server-title-group">
          <span className="server-name">{s.name}</span>
          <span className={`badge badge-${s.status}`}>
            ● {s.status}
          </span>
          {s.scope === 'tenant' && (
            <span className="badge badge-private">
              private
            </span>
          )}
        </div>

        <div>
          {s.connected ? (
            <span className="badge badge-connected">
              connected
            </span>
          ) : (
            <button className="btn-connect" onClick={() => onToggleConnect(s.id)}>
              Connect
            </button>
          )}
        </div>
      </div>

      {/* Description */}
      <p className="server-desc">{s.description}</p>

      {/* Meta Pills */}
      <div className="meta-row">
        <span className="meta-pill">{s.transport}</span>
        <span className="meta-pill">{s.auth_type}</span>
        <span className="meta-pill">{s.tools.length} tools</span>
      </div>

      {/* Tools List */}
      <div className="tools-list">
        {displayedTools.map(tool => (
          <div key={tool.id || tool.name} className="tool-item">
            <span className="tool-name">{tool.name}</span>
            <span className={`risk-tag ${tool.risk_level}`}>
              {tool.risk_level}
            </span>
          </div>
        ))}

        {!isExpanded && remainingCount > 0 && (
          <div className="tool-more-row" onClick={() => toggleExpand(s.id)}>
            + {remainingCount} more tools...
          </div>
        )}

        {isExpanded && remainingCount > 0 && (
          <div className="tool-more-row" onClick={() => toggleExpand(s.id)}>
            Show less
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="server-card-footer">
        <span>checked {s.last_checked_at || 'just now'}</span>
        <div className="card-actions">
          <button className="btn-text" onClick={() => onRefresh(s.id)}>
            ↻ Refresh
          </button>
          <button className="btn-text danger" onClick={() => onDelete(s.id)}>
            Delete
          </button>
        </div>
      </div>
    </div>
  )
}
