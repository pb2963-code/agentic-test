import { useEffect, useState } from 'react'
import { Dumbbell, Moon, Utensils, Smile, Footprints, Target } from 'lucide-react'
import { usePatient } from '../hooks/usePatient'
import { api } from '../services/api'

const ACTIVITY_TYPES = [
  'walking', 'running', 'cycling', 'swimming', 'strength', 'yoga', 'sports', 'hiking', 'other'
]

export function Wellness() {
  const { patient } = usePatient()
  const [dailySummary, setDailySummary] = useState<any>(null)
  const [weeklySummary, setWeeklySummary] = useState<any>(null)
  const [goals, setGoals] = useState<any[]>([])
  const [recommendations, setRecommendations] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState('activity')
  const [loading, setLoading] = useState(true)

  // Form states
  const [activityForm, setActivityForm] = useState({
    activity_type: 'walking',
    duration_minutes: 30,
    intensity: 'moderate',
  })
  const [sleepForm, setSleepForm] = useState({
    sleep_start: '',
    sleep_end: '',
    quality: 3,
  })
  const [moodForm, setMoodForm] = useState({
    mood_level: 3,
    energy_level: 5,
    stress_level: 5,
  })
  const [stepsForm, setStepsForm] = useState({
    steps: 0,
  })

  useEffect(() => {
    if (patient) {
      loadWellness()
    }
  }, [patient])

  const loadWellness = async () => {
    if (!patient) return
    try {
      const [daily, weekly, goalsData, recsData] = await Promise.all([
        api.getDailySummary(patient.patient_id),
        api.getWeeklySummary(patient.patient_id),
        api.getGoals(patient.patient_id),
        api.getWellnessRecommendations(patient.patient_id),
      ])
      setDailySummary(daily)
      setWeeklySummary(weekly)
      setGoals(goalsData.goals || [])
      setRecommendations(recsData.recommendations || [])
    } catch (err) {
      console.error('Failed to load wellness data:', err)
    } finally {
      setLoading(false)
    }
  }

  const submitActivity = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return
    try {
      await api.logActivity({
        patient_id: patient.patient_id,
        ...activityForm,
      })
      loadWellness()
    } catch (err) {
      console.error('Failed to log activity:', err)
    }
  }

  const submitSleep = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return
    try {
      await api.logSleep({
        patient_id: patient.patient_id,
        ...sleepForm,
      })
      loadWellness()
    } catch (err) {
      console.error('Failed to log sleep:', err)
    }
  }

  const submitMood = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return
    try {
      await api.logMood({
        patient_id: patient.patient_id,
        ...moodForm,
      })
      loadWellness()
    } catch (err) {
      console.error('Failed to log mood:', err)
    }
  }

  const submitSteps = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!patient) return
    try {
      await api.logSteps({
        patient_id: patient.patient_id,
        ...stepsForm,
      })
      loadWellness()
    } catch (err) {
      console.error('Failed to log steps:', err)
    }
  }

  if (loading) {
    return <div className="loading">Loading wellness data...</div>
  }

  return (
    <div>
      <div className="page-header">
        <h1>Wellness</h1>
        <p>Track your lifestyle and wellness activities</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-4">
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon primary">
              <Footprints size={24} />
            </div>
            <div>
              <div className="stat-value">{dailySummary?.steps || 0}</div>
              <div className="stat-label">Steps Today</div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon success">
              <Dumbbell size={24} />
            </div>
            <div>
              <div className="stat-value">{dailySummary?.exercise_minutes || 0}</div>
              <div className="stat-label">Exercise (min)</div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon info">
              <Moon size={24} />
            </div>
            <div>
              <div className="stat-value">{dailySummary?.sleep_hours || '-'}</div>
              <div className="stat-label">Sleep (hrs)</div>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="stat-card">
            <div className="stat-icon warning">
              <Smile size={24} />
            </div>
            <div>
              <div className="stat-value">{dailySummary?.mood || '-'}</div>
              <div className="stat-label">Mood</div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        {/* Log Forms */}
        <div className="card">
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
            {['activity', 'sleep', 'mood', 'steps'].map(tab => (
              <button
                key={tab}
                className={`btn ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {activeTab === 'activity' && (
            <form onSubmit={submitActivity}>
              <h3 className="card-title">Log Activity</h3>
              <div className="form-group">
                <label className="form-label">Activity Type</label>
                <select
                  className="form-input"
                  value={activityForm.activity_type}
                  onChange={e => setActivityForm({ ...activityForm, activity_type: e.target.value })}
                >
                  {ACTIVITY_TYPES.map(type => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Duration (minutes)</label>
                <input
                  type="number"
                  className="form-input"
                  value={activityForm.duration_minutes}
                  onChange={e => setActivityForm({ ...activityForm, duration_minutes: parseInt(e.target.value) })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Intensity</label>
                <select
                  className="form-input"
                  value={activityForm.intensity}
                  onChange={e => setActivityForm({ ...activityForm, intensity: e.target.value })}
                >
                  <option value="low">Low</option>
                  <option value="moderate">Moderate</option>
                  <option value="vigorous">Vigorous</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary">Log Activity</button>
            </form>
          )}

          {activeTab === 'sleep' && (
            <form onSubmit={submitSleep}>
              <h3 className="card-title">Log Sleep</h3>
              <div className="form-group">
                <label className="form-label">Bedtime</label>
                <input
                  type="datetime-local"
                  className="form-input"
                  value={sleepForm.sleep_start}
                  onChange={e => setSleepForm({ ...sleepForm, sleep_start: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Wake Time</label>
                <input
                  type="datetime-local"
                  className="form-input"
                  value={sleepForm.sleep_end}
                  onChange={e => setSleepForm({ ...sleepForm, sleep_end: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label className="form-label">Quality</label>
                <select
                  className="form-input"
                  value={sleepForm.quality}
                  onChange={e => setSleepForm({ ...sleepForm, quality: parseInt(e.target.value) })}
                >
                  <option value={1}>Poor</option>
                  <option value={2}>Fair</option>
                  <option value={3}>Good</option>
                  <option value={4}>Excellent</option>
                </select>
              </div>
              <button type="submit" className="btn btn-primary">Log Sleep</button>
            </form>
          )}

          {activeTab === 'mood' && (
            <form onSubmit={submitMood}>
              <h3 className="card-title">Log Mood</h3>
              <div className="form-group">
                <label className="form-label">Mood Level (1-5)</label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={moodForm.mood_level}
                  onChange={e => setMoodForm({ ...moodForm, mood_level: parseInt(e.target.value) })}
                  className="form-input"
                />
                <span>{['Very Low', 'Low', 'Neutral', 'Good', 'Excellent'][moodForm.mood_level - 1]}</span>
              </div>
              <div className="form-group">
                <label className="form-label">Energy Level (1-10)</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={moodForm.energy_level}
                  onChange={e => setMoodForm({ ...moodForm, energy_level: parseInt(e.target.value) })}
                  className="form-input"
                />
                <span>{moodForm.energy_level}/10</span>
              </div>
              <div className="form-group">
                <label className="form-label">Stress Level (1-10)</label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={moodForm.stress_level}
                  onChange={e => setMoodForm({ ...moodForm, stress_level: parseInt(e.target.value) })}
                  className="form-input"
                />
                <span>{moodForm.stress_level}/10</span>
              </div>
              <button type="submit" className="btn btn-primary">Log Mood</button>
            </form>
          )}

          {activeTab === 'steps' && (
            <form onSubmit={submitSteps}>
              <h3 className="card-title">Log Steps</h3>
              <div className="form-group">
                <label className="form-label">Steps</label>
                <input
                  type="number"
                  className="form-input"
                  value={stepsForm.steps}
                  onChange={e => setStepsForm({ ...stepsForm, steps: parseInt(e.target.value) })}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary">Log Steps</button>
            </form>
          )}
        </div>

        {/* Goals & Recommendations */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Goals Progress</h3>
            <Target size={20} color="#64748b" />
          </div>
          {goals.length > 0 ? (
            goals.map((goal, i) => (
              <div key={i} style={{ marginBottom: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <span>{goal.type}</span>
                  <span>{goal.current} / {goal.target} {goal.unit}</span>
                </div>
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${Math.min(100, goal.progress_percent)}%` }}
                  />
                </div>
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No goals set yet</p>
            </div>
          )}

          <h3 className="card-title" style={{ marginTop: '1.5rem' }}>Recommendations</h3>
          {recommendations.length > 0 ? (
            recommendations.map((rec, i) => (
              <div key={i} className="recommendation-item">
                <h4>{rec.category}</h4>
                <p>{rec.recommendation}</p>
                {rec.current && (
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                    Current: {rec.current}
                  </p>
                )}
              </div>
            ))
          ) : (
            <div className="empty-state">
              <p>No recommendations at this time</p>
            </div>
          )}
        </div>
      </div>

      {/* Weekly Summary */}
      {weeklySummary && (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Weekly Summary</h3>
          </div>
          <div className="grid grid-4">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--primary)' }}>
                {weeklySummary.total_steps?.toLocaleString() || 0}
              </div>
              <div className="stat-label">Total Steps</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--success)' }}>
                {weeklySummary.total_exercise_minutes || 0}
              </div>
              <div className="stat-label">Exercise Minutes</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--info)' }}>
                {weeklySummary.avg_sleep_hours || '-'}
              </div>
              <div className="stat-label">Avg Sleep (hrs)</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--warning)' }}>
                {weeklySummary.workout_days || 0}
              </div>
              <div className="stat-label">Workout Days</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
