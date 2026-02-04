import { useEffect, useState } from 'react'
import { AlertTriangle, Bell, CheckCircle, XCircle, Phone } from 'lucide-react'
import { usePatient } from '../hooks/usePatient'
import { api } from '../services/api'

interface Alert {
  alert_id: string
  category: string
  severity: number
  severity_name?: string
  title: string
  message: string
  status: string
  created_at: string
  actions?: { action: string; label: string }[]
}

const SEVERITY_LABELS = ['', 'Info', 'Warning', 'Urgent', 'Critical', 'Emergency']
const SEVERITY_CLASSES = ['', 'info', 'warning', 'warning', 'critical', 'critical']

export function Alerts() {
  const { patient } = usePatient()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [history, setHistory] = useState<Alert[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (patient) {
      loadAlerts()
    }
  }, [patient])

  const loadAlerts = async () => {
    if (!patient) return
    try {
      const [activeData, historyData] = await Promise.all([
        api.getAlerts(patient.patient_id),
        api.getAlerts(patient.patient_id).then(r => r), // Would need separate endpoint for history
      ])
      setAlerts(activeData.alerts || [])
      setHistory(historyData.alerts || [])
    } catch (err) {
      console.error('Failed to load alerts:', err)
    } finally {
      setLoading(false)
    }
  }

  const acknowledgeAlert = async (alertId: string) => {
    try {
      await api.acknowledgeAlert(alertId)
      loadAlerts()
    } catch (err) {
      console.error('Failed to acknowledge alert:', err)
    }
  }

  const resolveAlert = async (alertId: string) => {
    try {
      await api.resolveAlert(alertId)
      loadAlerts()
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    }
  }

  const triggerEmergency = async () => {
    if (!patient) return
    const reason = prompt('Please describe the emergency:')
    if (!reason) return

    try {
      await api.triggerEmergency({
        patient_id: patient.patient_id,
        reason,
      })
      loadAlerts()
    } catch (err) {
      console.error('Failed to trigger emergency:', err)
    }
  }

  if (loading) {
    return <div className="loading">Loading alerts...</div>
  }

  const activeAlerts = alerts.filter(a => a.status === 'active')
  const acknowledgedAlerts = alerts.filter(a => a.status === 'acknowledged')

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Alerts</h1>
            <p>Manage your health alerts and notifications</p>
          </div>
          <button
            className="btn"
            style={{ background: '#ef4444', color: 'white' }}
            onClick={triggerEmergency}
          >
            <Phone size={16} />
            Emergency
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-3">
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon danger">
              <AlertTriangle size={24} />
            </div>
            <div>
              <div className="stat-value">{activeAlerts.length}</div>
              <div className="stat-label">Active Alerts</div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon warning">
              <Bell size={24} />
            </div>
            <div>
              <div className="stat-value">{acknowledgedAlerts.length}</div>
              <div className="stat-label">Acknowledged</div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon success">
              <CheckCircle size={24} />
            </div>
            <div>
              <div className="stat-value">
                {alerts.filter(a => a.status === 'resolved').length}
              </div>
              <div className="stat-label">Resolved</div>
            </div>
          </div>
        </div>
      </div>

      {/* Critical Alerts */}
      {activeAlerts.filter(a => a.severity >= 4).length > 0 && (
        <div className="card" style={{ borderLeft: '4px solid #ef4444' }}>
          <h3 className="card-title" style={{ color: '#ef4444' }}>Critical Alerts</h3>
          {activeAlerts.filter(a => a.severity >= 4).map(alert => (
            <div key={alert.alert_id} className="alert-item critical">
              <AlertTriangle size={24} color="#ef4444" />
              <div style={{ flex: 1 }}>
                <h4>{alert.title}</h4>
                <p>{alert.message}</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {new Date(alert.created_at).toLocaleString()}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => acknowledgeAlert(alert.alert_id)}
                >
                  Acknowledge
                </button>
                <button
                  className="btn btn-primary"
                  onClick={() => resolveAlert(alert.alert_id)}
                >
                  Resolve
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Active Alerts */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Active Alerts</h3>
          <span className="badge warning">{activeAlerts.length} active</span>
        </div>

        {activeAlerts.length > 0 ? (
          activeAlerts.filter(a => a.severity < 4).map(alert => (
            <div
              key={alert.alert_id}
              className={`alert-item ${SEVERITY_CLASSES[alert.severity] || 'info'}`}
            >
              <Bell size={20} />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <h4>{alert.title}</h4>
                  <span className={`badge ${
                    alert.severity >= 3 ? 'danger' :
                    alert.severity >= 2 ? 'warning' : 'info'
                  }`}>
                    {SEVERITY_LABELS[alert.severity]}
                  </span>
                </div>
                <p>{alert.message}</p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  {alert.category} - {new Date(alert.created_at).toLocaleString()}
                </p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button
                  className="btn btn-secondary"
                  onClick={() => acknowledgeAlert(alert.alert_id)}
                >
                  <CheckCircle size={16} />
                </button>
                <button
                  className="btn btn-secondary"
                  onClick={() => resolveAlert(alert.alert_id)}
                >
                  <XCircle size={16} />
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <CheckCircle size={48} color="#22c55e" />
            <p style={{ marginTop: '1rem' }}>No active alerts. You're all caught up!</p>
          </div>
        )}
      </div>

      {/* Alert History Toggle */}
      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
        <button
          className="btn btn-secondary"
          onClick={() => setShowHistory(!showHistory)}
        >
          {showHistory ? 'Hide History' : 'Show Alert History'}
        </button>
      </div>

      {/* Alert History */}
      {showHistory && (
        <div className="card" style={{ marginTop: '1rem' }}>
          <h3 className="card-title">Alert History</h3>
          {history.length > 0 ? (
            history.map(alert => (
              <div key={alert.alert_id} className="insight-card">
                <div style={{ flex: 1 }}>
                  <h4>{alert.title}</h4>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                    {alert.message}
                  </p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    {alert.category} - {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>
                <span className={`badge ${
                  alert.status === 'resolved' ? 'success' :
                  alert.status === 'acknowledged' ? 'warning' : 'info'
                }`}>
                  {alert.status}
                </span>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No alert history</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
