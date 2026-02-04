import { useEffect, useState } from 'react'
import { Pill, Clock, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { usePatient } from '../hooks/usePatient'
import { api } from '../services/api'

interface Medication {
  medication_id: string
  name: string
  dosage: string
  frequency: string
  scheduled_times: string[]
  instructions?: string
  interactions?: string[]
}

interface UpcomingDose {
  medication_id: string
  medication_name: string
  dosage: string
  scheduled_time: string
  instructions?: string
}

export function Medications() {
  const { patient } = usePatient()
  const [medications, setMedications] = useState<Medication[]>([])
  const [upcomingDoses, setUpcomingDoses] = useState<UpcomingDose[]>([])
  const [adherence, setAdherence] = useState<any>(null)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    dosage: '',
    frequency: 'once_daily',
    scheduled_times: ['08:00'],
    start_date: new Date().toISOString().split('T')[0],
    instructions: '',
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (patient) {
      loadMedications()
    }
  }, [patient])

  const loadMedications = async () => {
    if (!patient) return
    try {
      const [medsData, upcomingData, adherenceData] = await Promise.all([
        api.getMedications(patient.patient_id),
        api.getUpcomingDoses(patient.patient_id),
        api.getAdherence(patient.patient_id),
      ])
      setMedications(medsData.medications || [])
      setUpcomingDoses(upcomingData.upcoming_doses || [])
      setAdherence(adherenceData)
    } catch (err) {
      console.error('Failed to load medications:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return

    try {
      await api.addMedication({
        patient_id: patient.patient_id,
        ...formData,
      })
      setShowForm(false)
      setFormData({
        name: '',
        dosage: '',
        frequency: 'once_daily',
        scheduled_times: ['08:00'],
        start_date: new Date().toISOString().split('T')[0],
        instructions: '',
      })
      loadMedications()
    } catch (err) {
      console.error('Failed to add medication:', err)
    }
  }

  const recordDose = async (dose: UpcomingDose, status: string) => {
    if (!patient) return
    try {
      await api.recordDose({
        patient_id: patient.patient_id,
        medication_id: dose.medication_id,
        scheduled_time: dose.scheduled_time,
        status,
        actual_time: new Date().toISOString(),
      })
      loadMedications()
    } catch (err) {
      console.error('Failed to record dose:', err)
    }
  }

  if (loading) {
    return <div className="loading">Loading medications...</div>
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Medications</h1>
            <p>Manage your medications and track adherence</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            Add Medication
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title">Add Medication</h3>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-2">
              <div className="form-group">
                <label className="form-label">Medication Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Dosage</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.dosage}
                  onChange={e => setFormData({ ...formData, dosage: e.target.value })}
                  placeholder="e.g., 10mg"
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Frequency</label>
                <select
                  className="form-input"
                  value={formData.frequency}
                  onChange={e => setFormData({ ...formData, frequency: e.target.value })}
                >
                  <option value="once_daily">Once Daily</option>
                  <option value="twice_daily">Twice Daily</option>
                  <option value="three_times_daily">Three Times Daily</option>
                  <option value="as_needed">As Needed</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Scheduled Time</label>
                <input
                  type="time"
                  className="form-input"
                  value={formData.scheduled_times[0]}
                  onChange={e => setFormData({ ...formData, scheduled_times: [e.target.value] })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Start Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={formData.start_date}
                  onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Instructions</label>
                <input
                  type="text"
                  className="form-input"
                  value={formData.instructions}
                  onChange={e => setFormData({ ...formData, instructions: e.target.value })}
                  placeholder="e.g., Take with food"
                />
              </div>
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

      <div className="grid grid-2">
        {/* Adherence Card */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Adherence Rate</h3>
          </div>
          {adherence?.adherence ? (
            <div style={{ textAlign: 'center', padding: '1rem' }}>
              <div className="wellness-score" style={{
                background: adherence.adherence.adherence_rate >= 80
                  ? 'linear-gradient(135deg, #22c55e, #4ade80)'
                  : adherence.adherence.adherence_rate >= 60
                    ? 'linear-gradient(135deg, #f59e0b, #fbbf24)'
                    : 'linear-gradient(135deg, #ef4444, #f87171)'
              }}>
                {adherence.adherence.adherence_rate}%
              </div>
              <p style={{ color: 'var(--text-secondary)' }}>
                {adherence.adherence.doses_taken} of {adherence.adherence.doses_total} doses taken
              </p>
              <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                Last {adherence.adherence.period_days} days
              </p>
            </div>
          ) : (
            <div className="empty-state">
              <p>No adherence data yet</p>
            </div>
          )}
        </div>

        {/* Upcoming Doses */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Upcoming Doses</h3>
            <Clock size={20} color="#64748b" />
          </div>
          {upcomingDoses.length > 0 ? (
            upcomingDoses.slice(0, 5).map((dose, index) => (
              <div key={index} className="medication-item">
                <div className="medication-info">
                  <h4>{dose.medication_name}</h4>
                  <p>{dose.dosage} - {new Date(dose.scheduled_time).toLocaleString()}</p>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    className="btn btn-primary"
                    style={{ padding: '0.25rem 0.5rem' }}
                    onClick={() => recordDose(dose, 'taken')}
                  >
                    <CheckCircle size={16} />
                  </button>
                  <button
                    className="btn btn-secondary"
                    style={{ padding: '0.25rem 0.5rem' }}
                    onClick={() => recordDose(dose, 'skipped')}
                  >
                    <XCircle size={16} />
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No upcoming doses</p>
            </div>
          )}
        </div>
      </div>

      {/* Medication List */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Your Medications</h3>
          <Pill size={20} color="#64748b" />
        </div>
        {medications.length > 0 ? (
          medications.map(med => (
            <div key={med.medication_id} className="medication-item">
              <div className="medication-info">
                <h4>{med.name}</h4>
                <p>{med.dosage} - {med.frequency.replace(/_/g, ' ')}</p>
                {med.instructions && (
                  <p style={{ fontSize: '0.75rem', fontStyle: 'italic' }}>{med.instructions}</p>
                )}
                {med.interactions && med.interactions.length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', marginTop: '0.25rem' }}>
                    <AlertCircle size={14} color="#f59e0b" />
                    <span style={{ fontSize: '0.75rem', color: '#f59e0b' }}>
                      {med.interactions.length} interaction(s)
                    </span>
                  </div>
                )}
              </div>
              <span className="badge success">Active</span>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No medications added yet</p>
          </div>
        )}
      </div>
    </div>
  )
}
