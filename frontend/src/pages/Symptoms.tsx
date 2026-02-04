import { useEffect, useState } from 'react'
import { Thermometer, AlertTriangle, CheckCircle } from 'lucide-react'
import { usePatient } from '../hooks/usePatient'
import { api } from '../services/api'

interface Symptom {
  symptom_id: string
  name: string
  category: string
  severity: number
  reported_at: string
  resolved_at?: string
}

const SEVERITY_LABELS = ['', 'Mild', 'Moderate', 'Severe', 'Critical']
const SEVERITY_COLORS = ['', 'success', 'warning', 'danger', 'danger']

const COMMON_SYMPTOMS = [
  'Headache', 'Fatigue', 'Nausea', 'Dizziness', 'Chest Pain',
  'Shortness of Breath', 'Fever', 'Cough', 'Back Pain', 'Joint Pain'
]

export function Symptoms() {
  const { patient } = usePatient()
  const [symptoms, setSymptoms] = useState<Symptom[]>([])
  const [analysis, setAnalysis] = useState<any>(null)
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({
    symptom_name: '',
    severity: 2,
    description: '',
    location: '',
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (patient) {
      loadSymptoms()
    }
  }, [patient])

  const loadSymptoms = async () => {
    if (!patient) return
    try {
      const [symptomsData, analysisData] = await Promise.all([
        api.getSymptoms(patient.patient_id),
        api.getSymptomAnalysis(patient.patient_id),
      ])
      setSymptoms(symptomsData.symptoms || [])
      setAnalysis(analysisData)
    } catch (err) {
      console.error('Failed to load symptoms:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return

    try {
      await api.reportSymptom({
        patient_id: patient.patient_id,
        ...formData,
      })
      setShowForm(false)
      setFormData({
        symptom_name: '',
        severity: 2,
        description: '',
        location: '',
      })
      loadSymptoms()
    } catch (err) {
      console.error('Failed to report symptom:', err)
    }
  }

  const resolveSymptom = async (symptomId: string) => {
    try {
      await api.resolveSymptom(symptomId)
      loadSymptoms()
    } catch (err) {
      console.error('Failed to resolve symptom:', err)
    }
  }

  if (loading) {
    return <div className="loading">Loading symptoms...</div>
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1>Symptoms</h1>
            <p>Track and analyze your symptoms</p>
          </div>
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            Report Symptom
          </button>
        </div>
      </div>

      {showForm && (
        <div className="card">
          <h3 className="card-title">Report Symptom</h3>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Symptom</label>
              <input
                type="text"
                className="form-input"
                value={formData.symptom_name}
                onChange={e => setFormData({ ...formData, symptom_name: e.target.value })}
                list="common-symptoms"
                placeholder="Enter or select a symptom"
                required
              />
              <datalist id="common-symptoms">
                {COMMON_SYMPTOMS.map(symptom => (
                  <option key={symptom} value={symptom} />
                ))}
              </datalist>
            </div>
            <div className="form-group">
              <label className="form-label">Severity</label>
              <select
                className="form-input"
                value={formData.severity}
                onChange={e => setFormData({ ...formData, severity: parseInt(e.target.value) })}
              >
                <option value={1}>Mild</option>
                <option value={2}>Moderate</option>
                <option value={3}>Severe</option>
                <option value={4}>Critical</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Description (optional)</label>
              <textarea
                className="form-input"
                value={formData.description}
                onChange={e => setFormData({ ...formData, description: e.target.value })}
                rows={3}
                placeholder="Describe your symptom..."
              />
            </div>
            <div className="form-group">
              <label className="form-label">Location (optional)</label>
              <input
                type="text"
                className="form-input"
                value={formData.location}
                onChange={e => setFormData({ ...formData, location: e.target.value })}
                placeholder="e.g., Head, Chest, Abdomen"
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="submit" className="btn btn-primary">Submit</button>
              <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-2">
        {/* Risk Assessment */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Risk Assessment</h3>
            <AlertTriangle size={20} color="#64748b" />
          </div>
          {analysis?.risk_assessment ? (
            <div>
              <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
                <span className={`badge ${
                  analysis.risk_assessment.overall_risk === 'critical' ? 'danger' :
                  analysis.risk_assessment.overall_risk === 'high' ? 'danger' :
                  analysis.risk_assessment.overall_risk === 'moderate' ? 'warning' : 'success'
                }`} style={{ fontSize: '1rem', padding: '0.5rem 1rem' }}>
                  {analysis.risk_assessment.overall_risk.toUpperCase()} RISK
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>
                {analysis.risk_assessment.active_symptoms} active symptom(s)
              </p>
              {analysis.risk_assessment.concerns && analysis.risk_assessment.concerns.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <h4 style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>Concerns:</h4>
                  <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)' }}>
                    {analysis.risk_assessment.concerns.map((concern: string, i: number) => (
                      <li key={i}>{concern}</li>
                    ))}
                  </ul>
                </div>
              )}
              {analysis.risk_assessment.recommendations && analysis.risk_assessment.recommendations.length > 0 && (
                <div style={{ marginTop: '1rem' }}>
                  <h4 style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>Recommendations:</h4>
                  {analysis.risk_assessment.recommendations.map((rec: string, i: number) => (
                    <div key={i} className="recommendation-item">
                      <p>{rec}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <p>No risk assessment available</p>
            </div>
          )}
        </div>

        {/* Patterns */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Detected Patterns</h3>
          </div>
          {analysis?.patterns && analysis.patterns.length > 0 ? (
            analysis.patterns.map((pattern: any, i: number) => (
              <div key={i} className="insight-card">
                <div>
                  <strong>{pattern.type}</strong>
                  <p>{pattern.description}</p>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Confidence: {Math.round(pattern.confidence * 100)}%
                  </p>
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No patterns detected yet. Continue tracking symptoms to identify patterns.</p>
            </div>
          )}
        </div>
      </div>

      {/* Active Symptoms */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Active Symptoms</h3>
          <Thermometer size={20} color="#64748b" />
        </div>
        {symptoms.length > 0 ? (
          symptoms.filter(s => !s.resolved_at).map(symptom => (
            <div key={symptom.symptom_id} className="medication-item">
              <div className="medication-info">
                <h4>{symptom.name}</h4>
                <p>
                  <span className={`badge ${SEVERITY_COLORS[symptom.severity]}`}>
                    {SEVERITY_LABELS[symptom.severity]}
                  </span>
                  <span style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>
                    {symptom.category || 'General'}
                  </span>
                </p>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                  Reported: {new Date(symptom.reported_at).toLocaleString()}
                </p>
              </div>
              <button
                className="btn btn-secondary"
                onClick={() => resolveSymptom(symptom.symptom_id)}
              >
                <CheckCircle size={16} />
                Resolve
              </button>
            </div>
          ))
        ) : (
          <div className="empty-state">
            <p>No active symptoms</p>
          </div>
        )}
      </div>
    </div>
  )
}
