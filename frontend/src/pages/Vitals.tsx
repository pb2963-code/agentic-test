import { useEffect, useState } from 'react'
import { Activity, Heart, Thermometer, Wind, Droplets } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { usePatient } from '../hooks/usePatient'
import { api } from '../services/api'

const VITAL_TYPES = [
  { id: 'heart_rate', name: 'Heart Rate', unit: 'bpm', icon: Heart, color: '#ef4444' },
  { id: 'blood_pressure_systolic', name: 'Blood Pressure (Systolic)', unit: 'mmHg', icon: Activity, color: '#3b82f6' },
  { id: 'blood_pressure_diastolic', name: 'Blood Pressure (Diastolic)', unit: 'mmHg', icon: Activity, color: '#8b5cf6' },
  { id: 'temperature', name: 'Temperature', unit: '\u00b0C', icon: Thermometer, color: '#f59e0b' },
  { id: 'oxygen_saturation', name: 'Oxygen Saturation', unit: '%', icon: Wind, color: '#22c55e' },
  { id: 'respiratory_rate', name: 'Respiratory Rate', unit: 'breaths/min', icon: Wind, color: '#06b6d4' },
]

export function Vitals() {
  const { patient } = usePatient()
  const [latestVitals, setLatestVitals] = useState<Record<string, any>>({})
  const [vitalHistory, setVitalHistory] = useState<any[]>([])
  const [trends, setTrends] = useState<Record<string, any>>({})
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    vital_type: 'heart_rate',
    value: '',
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (patient) {
      loadVitals()
    }
  }, [patient])

  const loadVitals = async () => {
    if (!patient) return
    try {
      const [latest, history, trendData] = await Promise.all([
        api.getLatestVitals(patient.patient_id),
        api.getVitals(patient.patient_id, 72),
        api.getVitalTrends(patient.patient_id),
      ])
      setLatestVitals(latest.latest_vitals || {})
      setVitalHistory(history.readings || [])
      setTrends(trendData.trends || {})
    } catch (err) {
      console.error('Failed to load vitals:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return

    const vitalType = VITAL_TYPES.find(v => v.id === formData.vital_type)

    try {
      await api.recordVital({
        patient_id: patient.patient_id,
        vital_type: formData.vital_type,
        value: parseFloat(formData.value),
        unit: vitalType?.unit || '',
      })
      setShowForm(false)
      setFormData({ vital_type: 'heart_rate', value: '' })
      loadVitals()
    } catch (err) {
      console.error('Failed to record vital:', err)
    }
  }

  const getTrendBadge = (trend: any) => {
    if (!trend || trend.direction === 'insufficient_data') return null
    const colors = {
      increasing: 'warning',
      decreasing: 'info',
      stable: 'success',
    }
    return (
      <span className={`badge ${colors[trend.direction as keyof typeof colors] || 'info'}`}>
        {trend.direction} ({trend.change_percent > 0 ? '+' : ''}{trend.change_percent}%)
      </span>
    )
  }

  if (loading) {
    return <div className="loading">Loading vitals...</div>
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Vital Signs</h1>
            <p>Monitor and track your vital signs</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            Record Vital
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title">Record Vital Sign</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Vital Type</label>
              <select
                className="form-input"
                value={formData.vital_type}
                onChange={e => setFormData({ ...formData, vital_type: e.target.value })}
              >
                {VITAL_TYPES.map(type => (
                  <option key={type.id} value={type.id}>{type.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Value</label>
              <input
                type="number"
                step="0.1"
                className="form-input"
                value={formData.value}
                onChange={e => setFormData({ ...formData, value: e.target.value })}
                placeholder={`Enter ${VITAL_TYPES.find(v => v.id === formData.vital_type)?.unit || 'value'}`}
                required
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="submit" className="btn btn-primary">Save</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Current Vitals Grid */}
      <div className="grid grid-3">
        {VITAL_TYPES.map(vitalType => {
          const data = latestVitals[vitalType.id]
          const trend = trends[vitalType.id]
          const Icon = vitalType.icon

          return (
            <div key={vitalType.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Icon size={20} color={vitalType.color} />
                  <span style={{ fontWeight: 500 }}>{vitalType.name}</span>
                </div>
                {getTrendBadge(trend)}
              </div>

              {data ? (
                <div className="vital-display">
                  <div className="vital-value" style={{ color: vitalType.color }}>
                    {data.value}
                    <span className="vital-unit">{vitalType.unit}</span>
                  </div>
                  <div className="vital-label">
                    Last updated: {new Date(data.recorded_at).toLocaleString()}
                  </div>
                </div>
              ) : (
                <div className="empty-state" style={{ padding: '1rem' }}>
                  <p>No reading</p>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Vital History Chart */}
      {vitalHistory.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Vital History (Last 72 Hours)</h3>
          </div>
          <div style={{ height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={vitalHistory.slice().reverse()}>
                <XAxis
                  dataKey="recorded_at"
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip
                  labelFormatter={(value) => new Date(value).toLocaleString()}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="#4f46e5"
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
