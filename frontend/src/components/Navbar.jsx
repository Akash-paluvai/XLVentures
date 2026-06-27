import { NavLink } from 'react-router-dom'

export default function Navbar({ activeDomain, onDomainChange }) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <h1 className="navbar-title">Decision Intelligence Platform</h1>
      </div>

      <div className="navbar-links">
        <NavLink to="/" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`} end>
          🎯 Recommend
        </NavLink>
        <NavLink to="/memory" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
          🧠 Memory
        </NavLink>
        <NavLink to="/trace" className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}>
          📊 Traces
        </NavLink>
      </div>

      <div className="navbar-domain">
        <label htmlFor="domain-select" className="domain-label">Domain:</label>
        <select
          id="domain-select"
          value={activeDomain}
          onChange={(e) => onDomainChange(e.target.value)}
          className="domain-select"
        >
          <option value="customer_success">Customer Success</option>
          <option value="recruitment">Recruitment</option>
        </select>
      </div>
    </nav>
  )
}
