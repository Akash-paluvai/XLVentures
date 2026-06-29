import { useState, useEffect } from 'react'
import { useAppStore } from '../../store/appStore'
import { fetchPreviousRecommendation } from '../../services/api'

export default function WhatChangedPanel() {
  const executionData = useAppStore((state) => state.executionData)
  const activeDomain = useAppStore((state) => state.activeDomain)

  const [prevRec, setPrevRec] = useState(null)
  const [loading, setLoading] = useState(false)

  const currentAction = executionData?.recommendation?.selected_action
  const currentConfidence = executionData?.recommendation_analysis?.confidence_breakdown?.score || 0

  // Fetch previous recommendation when execution data changes
  useEffect(() => {
    if (!executionData) {
      setPrevRec(null)
      return
    }

    const entityId = executionData.recommendation?.entity_id
      || executionData.thread_id // fallback

    // Try to extract entity_id from agent_steps planner input
    const plannerStep = executionData.agent_steps?.find(s => s.agent === 'planner')
    const inputSummary = plannerStep?.input_summary || ''
    const match = inputSummary.match(/\((acc_\w+|cand_\w+)\)/)
    const resolvedEntityId = match ? match[1] : entityId

    if (resolvedEntityId) {
      setLoading(true)
      fetchPreviousRecommendation(activeDomain, resolvedEntityId)
        .then((data) => {
          if (data && data.has_previous) {
            setPrevRec(data.previous)
          } else {
            setPrevRec(null)
          }
        })
        .finally(() => setLoading(false))
    }
  }, [executionData, activeDomain])

  if (!executionData) {
    return (
      <div className="changed-panel">
        <div className="sidebar-panel-title">What Changed</div>
        <p className="sidebar-panel-subtitle">
          Run the pipeline to compare with previous recommendations.
        </p>
        <div className="why-empty-state">
          <p>After running the pipeline, this panel will show what changed compared to the last recommendation for this entity.</p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="changed-panel">
        <div className="sidebar-panel-title">What Changed</div>
        <div style={{ textAlign: 'center', padding: '20px' }}>
          <div className="spinner" style={{ width: 24, height: 24 }} />
        </div>
      </div>
    )
  }

  if (!prevRec) {
    return (
      <div className="changed-panel">
        <div className="sidebar-panel-title">What Changed</div>
        <div className="changed-first-time">
          <div className="changed-first-icon">✦</div>
          <div className="changed-first-label">First recommendation for this entity</div>
          <p className="sidebar-panel-subtitle" style={{ marginTop: 8 }}>
            No previous recommendation exists to compare against.
          </p>
        </div>

        {/* Still show current */}
        {currentAction && (
          <div className="changed-current-card">
            <div className="changed-card-label">Current Recommendation</div>
            <div className="changed-card-title">{currentAction.title}</div>
            <div className="changed-card-desc">{currentAction.description}</div>
            <div className="changed-card-confidence">
              Confidence: {Math.round(currentConfidence * 100)}%
            </div>
          </div>
        )}
      </div>
    )
  }

  // Build "what changed" reasons from reasoning/entity signals
  const whyThis = executionData?.recommendation_analysis?.why_this || []

  return (
    <div className="changed-panel">
      <div className="sidebar-panel-title">What Changed</div>

      {/* Previous */}
      <div className="changed-prev-card">
        <div className="changed-card-label">Previous Recommendation</div>
        <div className="changed-card-title">{prevRec.action_title}</div>
        <div className="changed-card-desc">{prevRec.action_description}</div>
        <div className="changed-card-meta">
          <span className={`memory-outcome memory-outcome-${prevRec.outcome}`}>
            {prevRec.outcome}
          </span>
          <span className="changed-card-confidence">
            Confidence: {Math.round((prevRec.confidence || 0) * 100)}%
          </span>
        </div>
      </div>

      {/* Arrow */}
      <div className="changed-arrow">
        <div className="changed-arrow-line" />
        <div className="changed-arrow-icon">↓</div>
      </div>

      {/* Current */}
      {currentAction && (
        <div className="changed-current-card">
          <div className="changed-card-label">Current Recommendation</div>
          <div className="changed-card-title">{currentAction.title}</div>
          <div className="changed-card-desc">{currentAction.description}</div>
          <div className="changed-card-confidence">
            Confidence: {Math.round(currentConfidence * 100)}%
          </div>
        </div>
      )}

      {/* Why */}
      {whyThis.length > 0 && (
        <div className="changed-reasons">
          <div className="changed-reasons-title">Why the change?</div>
          {whyThis.slice(0, 5).map((reason, i) => (
            <div key={i} className="changed-reason-item">
              <span className="changed-reason-bullet">•</span>
              <span>{reason}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
