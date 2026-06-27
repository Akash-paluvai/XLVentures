import { useEffect, useState } from 'react'
import './index.css'

function App() {
  const [activeDomain, setActiveDomain] = useState('customer_success')
  const [domain, setDomain] = useState(null)
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async (domainName) => {
    try {
      setLoading(true)
      setError(null)
      setDomain(null)
      setAccounts([])
      
      // Fetch domain config using versioned API with query param
      const domainRes = await fetch(`http://localhost:8000/api/v1/domain?domain=${domainName}`)
      if (!domainRes.ok) {
        throw new Error(`Failed to fetch domain config: ${domainRes.status} ${domainRes.statusText}`)
      }
      const domainData = await domainRes.json()
      setDomain(domainData)

      // Fetch accounts/candidates using versioned API with query param
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
          <p className="subtitle">Project Scaffold &amp; Data Contract Verification (Shift 1)</p>
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
          <style>{`
            @keyframes spin {
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      ) : (
        !error && domain && (
          <>
            {/* Loaded Accounts Banner */}
            <div className="success-banner">
              <span className="success-badge">Shift 1 Done</span>
              <span>Loaded {accounts.length} {activeDomain === 'recruitment' ? 'candidates' : 'accounts'} for {domain.id} pack.</span>
            </div>

            {/* Stats Overview */}
            <div className="stats-grid">
              <div className="stat-card glass">
                <div className="stat-title">Domain Pack</div>
                <div className="stat-value" style={{ fontSize: '1.8rem', paddingTop: '6px' }}>{domain.name}</div>
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
                <div className="stat-desc">Dynamic routing targets</div>
              </div>
              <div className="stat-card glass">
                <div className="stat-title">Records Loaded</div>
                <div className="stat-value">{accounts.length}</div>
                <div className="stat-desc">Synthetic dataset</div>
              </div>
            </div>

            {/* Info Layout */}
            <div className="info-section">
              {/* Main List */}
              <div>
                <h2 className="section-title">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                  {activeDomain === 'recruitment' ? 'Candidates List' : 'Accounts Overview'}
                </h2>
                
                <div className="accounts-grid">
                  {accounts.map((item) => {
                    // Normalize fields between Account and Candidate schemas
                    const itemId = item.account_id || item.candidate_id
                    const name = item.company_name || item.candidate_name
                    const subtitle = item.industry || item.role_applied
                    const value = item.annual_contract_value || item.expected_salary
                    const valueLabel = activeDomain === 'recruitment' ? 'Expected Salary' : 'ACV'
                    const tierLabel = activeDomain === 'recruitment' ? 'Stage' : 'Tier'
                    const tier = item.plan_tier || item.current_stage
                    const trendLabel = activeDomain === 'recruitment' ? 'Interview Sentiment' : 'Usage Trend'
                    const trend = item.usage_trend || item.interview_sentiment
                    const scoreLabel = activeDomain === 'recruitment' ? 'Fit Score' : 'Health Score'
                    const score = item.health_score ?? item.fit_score ?? 50
                    const notes = item.interaction_notes || item.recruiter_notes
                    const dateLabel = activeDomain === 'recruitment' ? 'Offer Deadline' : 'Renewal Date'
                    const date = item.renewal_date || item.decision_deadline

                    return (
                      <div key={itemId} className="account-card glass">
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
                            <span className="tier-tag">{tier}</span>
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

                        <div>
                          <div className="notes-box">
                            {notes}
                          </div>
                          <div className="renewal-date-footer">
                            <span>{dateLabel}:</span>
                            <strong>{date}</strong>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Side Domain Details */}
              <div>
                <h2 className="section-title">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-purple)" strokeWidth="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                  </svg>
                  Domain Details
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
                      {domain.entities.map(ent => (
                        <span key={ent} className="domain-tag">{ent}</span>
                      ))}
                    </div>
                  </div>

                  <div className="domain-detail-item">
                    <div className="domain-detail-label">Success Metrics</div>
                    <div className="domain-tags">
                      {domain.success_metrics.map(metric => (
                        <span key={metric} className="domain-tag" style={{ color: '#6ee7b7', borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                          {metric.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="domain-detail-item">
                    <div className="domain-detail-label">Decision Points</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {domain.decision_points.map(dp => {
                        const dpName = typeof dp === 'string' ? dp : dp.name;
                        return (
                          <div key={dpName} style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            fontSize: '0.85rem',
                            color: 'var(--text-secondary)'
                          }}>
                            <span style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              backgroundColor: 'var(--accent-cyan)'
                            }} />
                            <span>{dpName.replace(/_/g, ' ')}</span>
                          </div>
                        )
                      })}
                    </div>
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
