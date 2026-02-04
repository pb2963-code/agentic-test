import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  Pill,
  AlertTriangle,
  Heart,
  LayoutDashboard,
  Dumbbell,
  Thermometer
} from 'lucide-react'

export function Layout() {
  return (
    <div className="app-container">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <Heart size={32} color="#4f46e5" />
          <h1>HealthMonitor</h1>
        </div>

        <nav>
          <NavLink
            to="/"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            end
          >
            <LayoutDashboard size={20} />
            Dashboard
          </NavLink>

          <NavLink
            to="/vitals"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Activity size={20} />
            Vital Signs
          </NavLink>

          <NavLink
            to="/medications"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Pill size={20} />
            Medications
          </NavLink>

          <NavLink
            to="/symptoms"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Thermometer size={20} />
            Symptoms
          </NavLink>

          <NavLink
            to="/wellness"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Dumbbell size={20} />
            Wellness
          </NavLink>

          <NavLink
            to="/alerts"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <AlertTriangle size={20} />
            Alerts
          </NavLink>
        </nav>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
