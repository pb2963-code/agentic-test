import { useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Heart,
  Pill,
  TrendingUp,
  Thermometer,
  Wind,
  Droplets
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { usePatient } from '../hooks/usePatient'
import { api } from '../services/api'

interface DashboardData {
  overview: {
    overall_status: string
    risk_level: string
    wellness_score: number
  }
  vitals: Record<string, { value: number; unit: string }>
  active_symptoms: number
  active_alerts: number
  recent_insights: any[]
  recommendations: any[]
}

export function Dashboard() {
  const { patient, loading: patientLoading } = usePatient()
  const [dashboard, setDashboard] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (patient) {
      loadDashboard()
    }
  }, [patient])

  const loadDashboard = async () => {
    if (!patient) return
    try {
      const data = await api.getDashboard(patient.patient_id)
      setDashboard(data)
    } catch (err) {
      console.error('Failed to load dashboard:', err)
    } finally {
      setLoading(false)
    }
  }

  if (patientLoading || loading) {
    return <div className="loading">Loading dashboard...</div>
  }

  if (!patient) {
    return (
      <div className="empty-state">
        <h2>No Patient Selected</h2>
        <p>Please register a patient to view the dashboard.</p>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'success'
      case 'stable_with_concerns': return 'warning'
      case 'needs_attention': return 'warning'
      case 'requires_immediate_attention': return 'danger'
      default: return 'info'
    }
  }

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low': return 'success'
      case 'moderate': return 'warning'
      case 'high': return 'danger'
      case 'critical': return 'danger'
      default: return 'info'
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Health Dashboard</h1>
        <p>Welcome back, {patient.first_name}! Here's your health overview.</p>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-4">
        <div className="card">
          <div className="stat-card">
            <div className={`stat-icon ${getStatusColor(dashboard?.overview?.overall_status || 'info')}`}>
              <Heart size={24} />
            </div>
            <div>
              <div className="stat-value">{dashboard?.overview?.wellness_score || 0}</div>
              <div className="stat-label">Wellness Score</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="stat-card">
            <div className={`stat-icon ${getRiskColor(dashboard?.overview?.risk_level || 'low')}`}>
              <TrendingUp size={24} />
            </div>
            <div>
              <div className="stat-value" style={{ textTransform: 'capitalize' }}>
                {dashboard?.overview?.risk_level || 'Low'}
              </div>
              <div className="stat-label">Risk Level</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="stat-card">
            <div className={`stat-icon ${(dashboard?.active_symptoms || 0) > 0 ? 'warning' : 'success'}`}>
              <Thermometer size={24} />
            </div>
            <div>
              <div className="stat-value">{dashboard?.active_symptoms || 0}</div>
              <div className="stat-label">Active Symptoms</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="stat-card">
            <div className={`stat-icon ${(dashboard?.active_alerts || 0) > 0 ? 'danger' : 'success'}`}>
              <AlertTriangle size={24} />
            </div>
            <div>
              <div className="stat-value">{dashboard?.active_alerts || 0}</div>
              <div className="stat-label">Active Alerts</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        {/* Current Vitals */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Current Vitals</h3>
            <Activity size={20} color="#64748b" />
          </div>

          {dashboard?.vitals && Object.keys(dashboard.vitals).length > 0 ? (
            <div className="grid grid-2">
              {Object.entries(dashboard.vitals).map(([type, data]) => (
                <div key={type} className="vital-display">
                  <div className="vital-value">
                    {data.value}
                    <span className="vital-unit">{data.unit}</span>
                  </div>
                  <div className="vital-label">
                    {type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <p>No vital readings recorded yet.</p>
            </div>
          )}
        </div>

        {/* Recommendations */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Recommendations</h3>
          </div>

          {dashboard?.recommendations && dashboard.recommendations.length > 0 ? (
            dashboard.recommendations.slice(0, 3).map((rec, index) => (
              <div key={index} className="recommendation-item">
                <h4>{rec.category}</h4>
                <p>{rec.recommendation}</p>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No recommendations at this time.</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Insights */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Recent Insights</h3>
        </div>

        {dashboard?.recent_insights && dashboard.recent_insights.length > 0 ? (
          dashboard.recent_insights.map((insight, index) => (
            <div key={index} className="insight-card">
              <div>
                <strong>{insight.type}</strong>
                <p>{insight.message || JSON.stringify(insight)}</p>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No recent insights. Continue tracking your health data to receive personalized insights.</p>
          </div>
        )}
      </div>
    </div>
  )
}
