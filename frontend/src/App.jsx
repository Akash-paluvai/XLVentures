import { useEffect, useState } from 'react'
import './index.css'

function App() {
  const [activeDomain, setActiveDomain] = useState('customer_success')
  const [domain, setDomain] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Shift 7 State
  const [selectedEntity, setSelectedEntity] = useState(null)
  const [recommendationData, setRecommendationData] = useState(null)
  const [recoLoading, setRecoLoading] = useState(false)
  const [submitLoading, setSubmitLoading] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [outcomeResult, setOutcomeResult] = useState(null)
  const [editingAction, setEditingAction] = useState(false)
  const [editedTitle, setEditedTitle] = useState('')
  const [editedDesc, setEditedDesc] = useState('')
  const [expandedEvidence, setExpandedEvidence] = useState({})
  
  const [reflectionData, setReflectionData] = useState(null)
  const [reflectLoading, setReflectLoading] = useState(false)

  const fetchData = async (domainName) => {
    try {
      setLoading(true)
      setError(null)
      setDomain(null)
      setAccounts([])
      setSelectedEntity(null)
      setRecommendationData(null)
      setReflectionData(null)
      
      const domainRes = await fetch(`http://localhost:8000/api/v1/domain?domain=${domainName}`)
      if (!domainRes.ok) {
        throw new Error(`Failed to fetch domain config: ${domainRes.status} ${domainRes.statusText}`)
      }
      const domainData = await domainRes.json()
      setDomain(domainData)

      const accountsRes = await fetch(`http://localhost:8000/api/v1/accounts?domain=${domainName}`)
      if (!accountsRes.ok) {
        throw new Error(`Failed to fetch accounts data: ${accountsRes.status} ${accountsRes.statusText}`)
      }
      const accountsData = await accountsRes.json()
      setAccounts(accountsData)
    } catch (err) {
      console.error(err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(activeDomain)
  }, [activeDomain])

  // Helper to color/style health score bar
  const getHealthColor = (score) => {
    if (score >= 80) return '#10b981' // emerald
    if (score >= 60) return '#f59e0b' // amber
    return '#f43f5e' // rose
  }

  // Format currency
  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0
    }).format(val)
  }

  // Dynamic Badge mapper based on domain type
  const getCardBadge = (item) => {
    if (!item) return null;
    
    if (activeDomain === 'recruitment') {
      const stage = item.current_stage ? item.current_stage.toLowerCase() : '';
      if (stage.includes('offer')) return <span className="badge badge-upsell">Offer Stage</span>
      if (stage.includes('technical')) return <span className="badge badge-champion">Technical Panel</span>
      return <span className="badge badge-healthy">Screening</span>
    } else {
      const id = item.account_id
      if (id === 'acc_cs_001') return <span className="badge badge-risk">Renewal Risk</span>
      if (id === 'acc_cs_002') return <span className="badge badge-upsell">Upsell Opp</span>
      if (id === 'acc_cs_003') return <span className="badge badge-champion">Champion Change</span>
      if (id === 'acc_cs_004') return <span className="badge badge-risk">Escalation Risk</span>
      if (id === 'acc_cs_005') return <span className="badge badge-healthy">Healthy Account</span>
      return <span className="badge badge-upsell">Expansion Opp</span>
    }
  }

  // Generate Recommendation Event Handler
  const handleGenerateRecommendation = async () => {
    if (!selectedEntity) return
    
    setRecoLoading(true)
    setRecommendationData(null)
    setOutcomeResult(null)
    setFeedbackText('')
    setEditingAction(false)
    
    try {
      const entityId = selectedEntity.account_id || selectedEntity.candidate_id
      const res = await fetch('http://localhost:8000/api/v1/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain_pack_id: activeDomain,
          entity_id: entityId
        })
      })
      
      if (!res.ok) {
        throw new Error(`Failed to generate recommendation: ${res.status} ${res.statusText}`)
      }
      
      const data = await res.json()
      setRecommendationData(data)
      
      // Pre-fill edit inputs with the generated selected action details
      if (data?.recommendation?.selected_action) {
        setEditedTitle(data.recommendation.selected_action.title)
        setEditedDesc(data.recommendation.selected_action.description)
      }
    } catch (err) {
      console.error(err)
      alert(err.message)
    } finally {
      setRecoLoading(false)
    }
  }

  // Submit Feedback Approval Event Handler
  const handleSubmitApproval = async (outcome) => {
    if (!recommendationData) return
    
    setSubmitLoading(true)
    try {
      const payload = {
        thread_id: recommendationData.thread_id,
        outcome: outcome,
        feedback_text: feedbackText || `${outcome.charAt(0).toUpperCase() + outcome.slice(1)} via Decision Hub UI.`
      }

      if (outcome === 'edited') {
        payload.edited_action = {
          ...recommendationData.recommendation.selected_action,
          title: editedTitle,
          description: editedDesc
        }
      }

      const res = await fetch('http://localhost:8000/api/v1/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      
      if (!res.ok) {
        throw new Error(`Failed to submit approval outcome: ${res.status} ${res.statusText}`)
      }
      
      const result = await res.json()
      setOutcomeResult(result)
    } catch (err) {
      console.error(err)
      alert(err.message)
    } finally {
      setSubmitLoading(false)
    }
  }

  // Run Reflection Event Handler
  const handleRunReflection = async () => {
    setReflectLoading(true)
    setReflectionData(null)
    try {
      const res = await fetch('http://localhost:8000/api/v1/reflect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain_pack_id: activeDomain
        })
      })
      
      if (!res.ok) {
        throw new Error(`Failed to trigger reflection job: ${res.status} ${res.statusText}`)
      }
      
      const data = await res.json()
      setReflectionData(data)
    } catch (err) {
      console.error(err)
      alert(err.message)
    } finally {
      setReflectLoading(false)
    }
  }

  // Toggle evidence expansion
  const toggleEvidence = (id) => {
    setExpandedEvidence(prev => ({
      ...prev,
      [id]: !prev[id]
    }))
  }

  return (
    <div className="dashboard-container">
      {/* Header & Domain Pack Toggle */}
      <header className="header animate-fadeIn" style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div>
          <h1 className="title" style={{ margin: 0 }}>Decision Intelligence Platform</h1>
          <p className="subtitle">Interactive Human-in-the-Loop Routing Workspace (Shift 7)</p>
        </div>

        {/* Dynamic Domain Switcher Dropdown */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          background: 'var(--bg-secondary)',
          padding: '8px 16px',
          borderRadius: '12px',
          border: '1px solid var(--border-color)'
        }}>
          <label htmlFor="domain-select" style={{
            fontSize: '0.85rem',
            fontWeight: '700',
            textTransform: 'uppercase',
            color: 'var(--text-secondary)'
          }}>
            Active Domain:
          </label>
          <select
            id="domain-select"
            value={activeDomain}
            onChange={(e) => setActiveDomain(e.target.value)}
            style={{
              background: '#0b0f19',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.15)',
              padding: '6px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              outline: 'none'
            }}
          >
            <option value="customer_success">Customer Success</option>
            <option value="recruitment">Recruitment (Staffing)</option>
          </select>
        </div>
      </header>

      {/* Connection error fallback */}
      {error && (
        <div style={{
          background: 'rgba(244, 63, 94, 0.1)',
          border: '1px solid rgba(244, 63, 94, 0.3)',
          borderRadius: '12px',
          padding: '24px',
          textAlign: 'left',
          marginBottom: '30px',
          color: '#fca5a5'
        }}>
          <h3 style={{ margin: '0 0 10px 0', fontSize: '1.2rem' }}>Backend Connection Error</h3>
          <p style={{ margin: '0 0 15px 0', fontSize: '0.95rem' }}>
            The frontend could not connect to the FastAPI backend API. Please make sure the backend server is running locally on port 8000.
          </p>
          <code style={{ background: '#1e1b1b', color: '#ff79c6', padding: '6px 12px', borderRadius: '6px', fontSize: '0.9rem' }}>
            uvicorn backend.api.main:app --reload --port 8000
          </code>
          <div style={{ marginTop: '15px', fontSize: '0.85rem', color: '#b91c1c' }}>
            Details: {error}
          </div>
        </div>
      )}

      {loading ? (
        <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid rgba(139, 92, 246, 0.1)',
            borderTopColor: 'var(--accent-purple)',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
            margin: '0 auto 20px auto'
          }} />
          <p>Loading {activeDomain.replace(/_/g, ' ')} domain metadata...</p>
        </div>
      ) : (
        !error && domain && (
          <>
            {/* Stats Overview */}
            <div className="stats-grid">
              <div className="stat-card glass">
                <div className="stat-title">Domain Pack</div>
                <div className="stat-value" style={{ fontSize: '1.6rem', paddingTop: '4px' }}>{domain.name}</div>
                <div className="stat-desc">Active business pack</div>
              </div>
              <div className="stat-card glass">
                <div className="stat-title">Workflows</div>
                <div className="stat-value">{domain.workflows.length}</div>
                <div className="stat-desc">{domain.workflows.join(', ')}</div>
              </div>
              <div className="stat-card glass">
                <div className="stat-title">Decision Points</div>
                <div className="stat-value">{domain.decision_points.length}</div>
                <div className="stat-desc">Orchestration targets</div>
              </div>
              <div className="stat-card glass">
                <div className="stat-title">Records Loaded</div>
                <div className="stat-value">{accounts.length}</div>
                <div className="stat-desc">Synthetic entities</div>
              </div>
            </div>

            {/* Info Layout */}
            <div className="info-section">
              {/* Left Column: Accounts List OR Interactive Recommendation Hub */}
              <div>
                {!selectedEntity ? (
                  <div>
                    <h2 className="section-title">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                        <circle cx="9" cy="7" r="4" />
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                      </svg>
                      {activeDomain === 'recruitment' ? 'Select Candidate for Evaluation' : 'Select Customer Account to Evaluate'}
                    </h2>
                    
                    <div className="accounts-grid">
                      {accounts.map((item) => {
                        const itemId = item.account_id || item.candidate_id
                        const name = item.company_name || item.candidate_name
                        const subtitle = item.industry || item.role_applied
                        const value = item.annual_contract_value || item.expected_salary
                        const score = item.health_score ?? item.fit_score ?? 50
                        const scoreLabel = activeDomain === 'recruitment' ? 'Fit Score' : 'Health Score'
                        const trendLabel = activeDomain === 'recruitment' ? 'Sentiment' : 'Trend'
                        const trend = item.usage_trend || item.interview_sentiment

                        return (
                          <div 
                            key={itemId} 
                            className="account-card glass"
                            onClick={() => {
                              setSelectedEntity(item)
                              setRecommendationData(null)
                              setFeedbackText('')
                              setOutcomeResult(null)
                              setEditingAction(false)
                            }}
                            style={{ cursor: 'pointer' }}
                          >
                            <div>
                              <div className="account-header">
                                <div>
                                  <h3 className="account-name">{name}</h3>
                                  <span className="account-industry">{subtitle}</span>
                                </div>
                                {getCardBadge(item)}
                              </div>

                              <div className="acv-tier">
                                <span className="acv-val">{formatCurrency(value)}</span>
                                <span className="tier-tag">{item.plan_tier || item.current_stage}</span>
                              </div>

                              <div className="usage-trend-box">
                                <div className="usage-label">{trendLabel}</div>
                                <div className="usage-value">{trend}</div>
                              </div>

                              <div className="health-row">
                                <span className="health-label">{scoreLabel}: <strong>{score}</strong></span>
                                <div className="health-progress-bg">
                                  <div className="health-progress-bar" style={{
                                    width: `${score}%`,
                                    backgroundColor: getHealthColor(score)
                                  }} />
                                </div>
                              </div>
                            </div>
                            
                            <div style={{ marginTop: '16px' }}>
                              <button className="btn-ui btn-primary-ui" style={{ width: '100%', justifyContent: 'center' }}>
                                Open Decision Workspace →
                              </button>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ) : (
                  /* Shift 7 Interactive Recommendation Workspace */
                  <div className="recommendation-panel glass" style={{ padding: '30px', border: '1px solid var(--accent-purple)' }}>
                    <div className="recommendation-header">
                      <div>
                        <h2 style={{ margin: 0, fontSize: '1.8rem', fontFamily: 'var(--heading-font)' }}>
                          🎯 Decision Workspace: {selectedEntity.company_name || selectedEntity.candidate_name}
                        </h2>
                        <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                          ID: {selectedEntity.account_id || selectedEntity.candidate_id} | Stage: {selectedEntity.plan_tier || selectedEntity.current_stage}
                        </p>
                      </div>
                      <button className="btn-ui btn-secondary-ui" onClick={() => setSelectedEntity(null)}>
                        ← Back to List
                      </button>
                    </div>

                    {/* Pre-recommendation Trigger View */}
                    {!recommendationData && !recoLoading && (
                      <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                        <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🤖</div>
                        <h3 style={{ margin: '0 0 10px 0', fontSize: '1.3rem' }}>Ready for Evaluation</h3>
                        <p style={{ maxWidth: '450px', margin: '0 auto 24px auto', fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: '145%' }}>
                          Kick off the LangGraph planner agent to classify this situation.
                          The system will dynamically retrieve context and either execute the full 5-agent reasoning flow or route to routine cadence.
                        </p>
                        <button className="btn-ui btn-primary-ui" onClick={handleGenerateRecommendation} style={{ fontSize: '1.05rem', padding: '12px 24px' }}>
                          Run Decision Pipeline
                        </button>
                      </div>
                    )}

                    {/* Loading State */}
                    {recoLoading && (
                      <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-secondary)' }}>
                        <div className="health-progress-bg" style={{ width: '200px', margin: '0 auto 20px auto', height: '8px' }}>
                          <div className="health-progress-bar" style={{
                            width: '60%',
                            backgroundColor: 'var(--accent-purple)',
                            animation: 'pulse 1.5s infinite ease-in-out'
                          }} />
                        </div>
                        <p style={{ fontSize: '0.95rem' }}>Executing LangGraph pipeline nodes... Classifying triggers...</p>
                        <style>{`
                          @keyframes pulse {
                            0% { transform: scaleX(0.1); transform-origin: left; }
                            50% { transform: scaleX(1); transform-origin: left; }
                            100% { transform: scaleX(0.1); transform-origin: right; }
                          }
                        `}</style>
                      </div>
                    )}

                    {/* Recommendation Output Display */}
                    {recommendationData && (
                      <div>
                        {/* Status / Path Banner */}
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          background: recommendationData.routing_path === 'escalation' ? 'rgba(244,63,94,0.08)' : 'rgba(16,185,129,0.08)',
                          border: `1px solid ${recommendationData.routing_path === 'escalation' ? 'rgba(244,63,94,0.3)' : 'rgba(16,185,129,0.3)'}`,
                          borderRadius: '8px',
                          padding: '12px 20px',
                          marginBottom: '24px',
                          fontSize: '0.95rem'
                        }}>
                          <span>Orchestration Mode:</span>
                          <strong style={{
                            color: recommendationData.routing_path === 'escalation' ? '#fca5a5' : '#a7f3d0',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px'
                          }}>
                            {recommendationData.routing_path === 'escalation' ? '⚠️ Escalation Path Triggered' : '✅ Standard Cadence Route'}
                          </strong>
                        </div>

                        {/* Recommendation Split Grid */}
                        <div className="recommendation-grid">
                          {/* Left Column: Ranked Options & HITL Approval */}
                          <div>
                            {/* Confidence Gauge Block */}
                            <h3 className="domain-detail-label" style={{ marginBottom: '12px' }}>Computed Recommendation Confidence</h3>
                            <div className="confidence-gauge-container">
                              <div className="confidence-circle">
                                {(() => {
                                  const score = recommendationData.recommendation?.computed_confidence?.score ?? 0.8;
                                  const scorePct = Math.round(score * 100);
                                  const strokeDash = (scorePct / 100) * 220;
                                  return (
                                    <>
                                      <svg className="confidence-circle-svg">
                                        <circle cx="40" cy="40" r="35" stroke="rgba(255,255,255,0.05)" strokeWidth="6" fill="transparent" />
                                        <circle cx="40" cy="40" r="35" stroke="var(--accent-emerald)" strokeWidth="6" fill="transparent" 
                                          strokeDasharray="220" strokeDashoffset={220 - strokeDash} strokeLinecap="round" />
                                      </svg>
                                      <div className="confidence-val-text">{scorePct}%</div>
                                    </>
                                  )
                                })()}
                              </div>
                              <div className="confidence-metrics">
                                <div className="confidence-metric-row">
                                  <span>Evidence Retrievability:</span>
                                  <strong>{recommendationData.recommendation?.computed_confidence?.evidence_count ?? 0} references</strong>
                                </div>
                                <div className="confidence-metric-row">
                                  <span>Source Agreement:</span>
                                  <strong>{Math.round((recommendationData.recommendation?.computed_confidence?.source_agreement ?? 1.0) * 100)}%</strong>
                                </div>
                                <div className="confidence-metric-row">
                                  <span>Historical Acceptance Rate:</span>
                                  <strong>{Math.round((recommendationData.recommendation?.computed_confidence?.historical_acceptance_rate ?? 0.5) * 100)}%</strong>
                                </div>
                              </div>
                            </div>

                            {/* Ranked Candidates Panel */}
                            <div className="candidates-list-container">
                              <h3 className="domain-detail-label" style={{ marginBottom: '12px' }}>Ranked Next-Best Actions</h3>
                              <div className="candidate-actions-grid">
                                {recommendationData.recommendation?.candidate_actions?.map((act) => {
                                  const isSelected = act.id === (recommendationData.recommendation?.selected_action_id || recommendationData.recommendation?.selected_action?.id)
                                  return (
                                    <div key={act.id} className={`candidate-card-ui ${isSelected ? 'selected' : 'rejected'}`}>
                                      <div className="candidate-card-header">
                                        <h4 className="candidate-card-title">{act.title}</h4>
                                        <span className={`candidate-badge ${isSelected ? 'candidate-badge-selected' : 'candidate-badge-rejected'}`}>
                                          {isSelected ? 'Selected Primary' : `Ranked Option`}
                                        </span>
                                      </div>
                                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0 0 8px 0', lineHeight: '140%' }}>
                                        {act.description}
                                      </p>
                                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                                        <strong>Rationale:</strong> {act.rationale}
                                      </div>
                                      
                                      {/* Specific Rejection Reasons */}
                                      {!isSelected && act.rejected_reason && (
                                        <div className="rejected-reason-box">
                                          ⚠️ <strong>Rejection Reason:</strong> {act.rejected_reason}
                                        </div>
                                      )}

                                      {/* Edit Controls for Selected Action */}
                                      {isSelected && (
                                        <div style={{ marginTop: '12px' }}>
                                          <button 
                                            className="btn-ui btn-secondary-ui" 
                                            onClick={() => setEditingAction(!editingAction)}
                                            style={{ fontSize: '0.75rem', padding: '4px 10px' }}
                                          >
                                            ✏️ {editingAction ? 'Cancel Edit' : 'Edit Action Details'}
                                          </button>
                                          
                                          {editingAction && (
                                            <div className="edit-action-form">
                                              <div>
                                                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Edit Title:</label>
                                                <input 
                                                  type="text" 
                                                  className="edit-input" 
                                                  value={editedTitle} 
                                                  onChange={(e) => setEditedTitle(e.target.value)} 
                                                />
                                              </div>
                                              <div>
                                                <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>Edit Description:</label>
                                                <textarea 
                                                  className="edit-input" 
                                                  style={{ height: '50px', resize: 'none' }}
                                                  value={editedDesc} 
                                                  onChange={(e) => setEditedDesc(e.target.value)} 
                                                />
                                              </div>
                                              <button 
                                                className="btn-ui btn-success-ui" 
                                                onClick={() => {
                                                  // Update selected action title and description local state
                                                  recommendationData.recommendation.selected_action.title = editedTitle
                                                  recommendationData.recommendation.selected_action.description = editedDesc
                                                  setEditingAction(false)
                                                }}
                                                style={{ fontSize: '0.75rem', padding: '4px 10px', alignSelf: 'flex-start' }}
                                              >
                                                Save Changes
                                              </button>
                                            </div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )
                                })}
                              </div>
                            </div>

                            {/* HITL Form and Actions */}
                            {!outcomeResult ? (
                              <div className="feedback-box-ui">
                                <h3 className="domain-detail-label" style={{ marginBottom: '8px' }}>Human-in-the-loop Gate</h3>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0 0 12px 0' }}>
                                  Review recommendation logic. Enter custom feedback notes, and choose an outcome decision.
                                </p>
                                <textarea 
                                  className="feedback-textarea"
                                  placeholder="Enter human feedback reasoning..."
                                  value={feedbackText}
                                  onChange={(e) => setFeedbackText(e.target.value)}
                                />
                                <div className="feedback-actions">
                                  <button 
                                    className="btn-ui btn-success-ui"
                                    onClick={() => handleSubmitApproval(editingAction || editedTitle !== recommendationData.recommendation?.selected_action?.title ? 'edited' : 'approved')}
                                    disabled={submitLoading}
                                  >
                                    ✅ {editingAction || editedTitle !== recommendationData.recommendation?.selected_action?.title ? 'Approve Edited Action' : 'Approve Action'}
                                  </button>
                                  <button 
                                    className="btn-ui btn-warning-ui"
                                    onClick={() => handleSubmitApproval('needs_info')}
                                    disabled={submitLoading}
                                  >
                                    ❓ Request Info
                                  </button>
                                  <button 
                                    className="btn-ui btn-danger-ui"
                                    onClick={() => handleSubmitApproval('rejected')}
                                    disabled={submitLoading}
                                  >
                                    ❌ Reject Option
                                  </button>
                                </div>
                              </div>
                            ) : (
                              /* HITL Success Outcomes */
                              <div style={{
                                background: 'rgba(16, 185, 129, 0.1)',
                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                borderRadius: '12px',
                                padding: '24px',
                                marginTop: '24px',
                                textAlign: 'left'
                              }}>
                                <h3 style={{ margin: '0 0 8px 0', fontSize: '1.2rem', color: '#6ee7b7' }}>🎉 Decision Successfully Logged</h3>
                                <p style={{ margin: '0 0 16px 0', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                  The LangGraph pipeline checkpointer has resumed. The episodic SQLite database was written to, and reflection variables populated.
                                </p>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.85rem' }}>
                                  <div>Outcome: <strong style={{ color: '#fff' }}>{outcomeResult.outcome.toUpperCase()}</strong></div>
                                  <div>Feedback ID: <code style={{ color: 'var(--accent-cyan)' }}>{outcomeResult.metadata?.outcome_feedback_id}</code></div>
                                  <div>Reflection Sync: <span style={{ color: 'var(--accent-emerald)' }}>{outcomeResult.metadata?.reflection_status}</span></div>
                                </div>
                                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '16px 0 0 0', fontStyle: 'italic' }}>
                                  Tip: Trigger a manual Reflection Job in the right panel to update ChromeDB heuristics.
                                </p>
                              </div>
                            )}
                          </div>

                          {/* Right Column: Reasoning Trace & Evidence Accordions */}
                          <div>
                            {/* Reasoning Trace timeline */}
                            <div style={{ marginBottom: '30px' }}>
                              <h3 className="domain-detail-label" style={{ marginBottom: '12px' }}>Chronological Reasoning Trace</h3>
                              <div className="timeline-container">
                                {recommendationData.recommendation?.reasoning_trace?.map((trace, idx) => (
                                  <div key={idx} className="timeline-item">
                                    <div className="timeline-dot" />
                                    <div className="timeline-content">{trace}</div>
                                  </div>
                                ))}
                              </div>
                            </div>

                            {/* Evidence display as clean expandable accordions */}
                            <div className="evidence-container-ui">
                              <h3 className="domain-detail-label" style={{ marginBottom: '12px' }}>Retrieved Context Evidence References</h3>
                              {recommendationData.recommendation?.evidence?.length > 0 ? (
                                recommendationData.recommendation.evidence.map((node, idx) => {
                                  const id = node.evidence_id || `node_${idx}`
                                  const isExpanded = !!expandedEvidence[id]
                                  const icon = node.source_type === 'playbook' ? '📘' : '🗂️'
                                  const reliability = node.confidence ? Math.round(node.confidence * 100) : 80;
                                  
                                  return (
                                    <div key={id} className="evidence-accordion-item">
                                      <button className="evidence-accordion-header" onClick={() => toggleEvidence(id)}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                          <span>{icon}</span>
                                          <strong>{id}</strong>
                                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            ({node.source_type} ➔ {node.retrieval_type})
                                          </span>
                                        </div>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                          <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>Reliability: {reliability}%</span>
                                          <span>{isExpanded ? '▼' : '►'}</span>
                                        </div>
                                      </button>
                                      {isExpanded && (
                                        <div className="evidence-accordion-content">
                                          <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{node.content}</p>
                                        </div>
                                      )}
                                    </div>
                                  )
                                })
                              ) : (
                                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', margin: 0 }}>No evidence nodes recorded.</p>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Right Column: Side Domain Details & Continuous Learning Reflection Panel */}
              <div>
                <h2 className="section-title">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  Domain Settings
                </h2>
                <div className="domain-card glass">
                  <div className="domain-detail-item">
                    <div className="domain-detail-label">Pack Description</div>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', margin: 0, lineHeight: '145%' }}>
                      {domain.description}
                    </p>
                  </div>
                  
                  <div className="domain-detail-item">
                    <div className="domain-detail-label">Entities</div>
                    <div className="domain-tags">
                      {domain.entities?.map(ent => (
                        <span key={ent} className="domain-tag">{ent}</span>
                      ))}
                    </div>
                  </div>

                  <div className="domain-detail-item">
                    <div className="domain-detail-label">Success Metrics</div>
                    <div className="domain-tags">
                      {domain.success_metrics?.map(metric => (
                        <span key={metric} className="domain-tag" style={{ color: '#6ee7b7', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                          {metric.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Shift 7 Manual Reflection Trigger Block */}
                  <div className="domain-detail-item" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px', marginTop: '20px' }}>
                    <div className="domain-detail-label" style={{ color: 'var(--accent-cyan)' }}>Continuous Learning Hub</div>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '135%' }}>
                      Run episodic reflection. Aggregates SQLite histories, mines approval rates, and generates optimized heuristics playbooks in ChromaDB.
                    </p>
                    <button 
                      className="btn-ui btn-primary-ui" 
                      onClick={handleRunReflection}
                      disabled={reflectLoading}
                      style={{ width: '100%', justifyContent: 'center' }}
                    >
                      {reflectLoading ? 'Mining Rules...' : '💡 Run Reflection Job'}
                    </button>
                    {reflectionData && (
                      <div className="reflection-report animate-fadeIn">
                        <h4 style={{ margin: '0 0 10px 0', fontSize: '0.95rem', color: 'var(--accent-emerald)' }}>
                          ✅ reflection_status: {reflectionData.status}
                        </h4>
                        <div className="reflection-md">
                          {reflectionData.heuristics || "Reflection complete. No new patterns found."}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </>
        )
      )}
    </div>
  )
}

export default App
