import { useAppStore } from '../store/appStore'
import OverviewPanel from './sidebar/OverviewPanel'
import AgentsPanel from './sidebar/AgentsPanel'
import WhyThisPanel from './sidebar/WhyThisPanel'
import WhatChangedPanel from './sidebar/WhatChangedPanel'

const NAV_ITEMS = [
  { id: 'overview', icon: '', label: 'Overview' },
  { id: 'agents', icon: '', label: 'Agent Execution' },
  { id: 'why', icon: '', label: 'Why This?' },
  { id: 'changed', icon: '', label: 'What Changed' },
]

const PANELS = {
  overview: OverviewPanel,
  agents: AgentsPanel,
  why: WhyThisPanel,
  changed: WhatChangedPanel,
}

export default function ExecutionSidebar() {
  const { sidebarOpen, sidebarPanel, setSidebarPanel, toggleSidebar } = useAppStore()

  const ActivePanel = PANELS[sidebarPanel] || OverviewPanel

  return (
    <aside className={`exec-sidebar ${sidebarOpen ? 'exec-sidebar--open' : 'exec-sidebar--closed'}`}>
      {/* Collapse toggle */}
      <button className="sidebar-toggle" onClick={toggleSidebar} title={sidebarOpen ? 'Collapse' : 'Expand'}>
        {sidebarOpen ? '›' : '‹'}
      </button>

      {sidebarOpen && (
        <>
          {/* Header */}
          <div className="sidebar-header">
            <span className="sidebar-header-title">AI Execution Center</span>
          </div>

          {/* Navigation */}
          <nav className="sidebar-nav">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                className={`sidebar-nav-item ${sidebarPanel === item.id ? 'sidebar-nav-item--active' : ''}`}
                onClick={() => setSidebarPanel(item.id)}
              >
                <span className="sidebar-nav-icon">{item.icon}</span>
                <span className="sidebar-nav-label">{item.label}</span>
              </button>
            ))}
          </nav>

          {/* Divider */}
          <div className="sidebar-divider" />

          {/* Active Panel */}
          <div className="sidebar-panel-content">
            <ActivePanel />
          </div>
        </>
      )}
    </aside>
  )
}
