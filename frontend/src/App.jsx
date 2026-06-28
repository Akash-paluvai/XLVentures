import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import RecommendPage from './pages/RecommendPage'
import MemoryPage from './pages/MemoryPage'
import TracePage from './pages/TracePage'
import ConfigurationPage from './pages/ConfigurationPage'
import './index.css'

function App() {
  return (
    <Router>
      <div className="app-shell">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<RecommendPage />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/trace" element={<TracePage />} />
            <Route path="/config" element={<ConfigurationPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
