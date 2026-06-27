import { useState } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import RecommendPage from './pages/RecommendPage'
import MemoryPage from './pages/MemoryPage'
import TracePage from './pages/TracePage'
import './index.css'

function App() {
  const [activeDomain, setActiveDomain] = useState('customer_success')

  return (
    <Router>
      <div className="app-shell">
        <Navbar activeDomain={activeDomain} onDomainChange={setActiveDomain} />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<RecommendPage activeDomain={activeDomain} />} />
            <Route path="/memory" element={<MemoryPage activeDomain={activeDomain} />} />
            <Route path="/trace" element={<TracePage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
