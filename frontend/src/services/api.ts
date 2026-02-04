const API_BASE = '/api'

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`)
  }

  return response.json()
}

export const api = {
  // Patients
  getPatients: () => fetchApi<{ patients: any[]; count: number }>('/patients'),
  getPatient: (id: string) => fetchApi<{ patient: any }>(`/patients/${id}`),
  createPatient: (data: any) => fetchApi<any>('/patients', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Dashboard
  getDashboard: (patientId: string) => fetchApi<any>(`/dashboard/${patientId}`),
  getHealthSummary: (patientId: string) => fetchApi<any>(`/dashboard/${patientId}/summary`),
  getRiskAssessment: (patientId: string) => fetchApi<any>(`/dashboard/${patientId}/risk`),
  getRecommendations: (patientId: string) => fetchApi<any>(`/dashboard/${patientId}/recommendations`),

  // Vitals
  recordVital: (data: any) => fetchApi<any>('/vitals', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getVitals: (patientId: string, hours = 24) =>
    fetchApi<any>(`/vitals/${patientId}?hours=${hours}`),
  getLatestVitals: (patientId: string) =>
    fetchApi<any>(`/vitals/${patientId}/latest`),
  getVitalTrends: (patientId: string) =>
    fetchApi<any>(`/vitals/${patientId}/trends`),

  // Medications
  getMedications: (patientId: string) =>
    fetchApi<any>(`/medications/${patientId}`),
  addMedication: (data: any) => fetchApi<any>('/medications', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  recordDose: (data: any) => fetchApi<any>('/medications/dose', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getUpcomingDoses: (patientId: string) =>
    fetchApi<any>(`/medications/${patientId}/upcoming`),
  getAdherence: (patientId: string) =>
    fetchApi<any>(`/medications/${patientId}/adherence`),

  // Symptoms
  reportSymptom: (data: any) => fetchApi<any>('/symptoms', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getSymptoms: (patientId: string) =>
    fetchApi<any>(`/symptoms/${patientId}`),
  getSymptomAnalysis: (patientId: string) =>
    fetchApi<any>(`/symptoms/${patientId}/analysis`),
  resolveSymptom: (symptomId: string) =>
    fetchApi<any>(`/symptoms/${symptomId}/resolve`, { method: 'POST' }),

  // Alerts
  getAlerts: (patientId: string) =>
    fetchApi<any>(`/alerts/${patientId}`),
  acknowledgeAlert: (alertId: string) =>
    fetchApi<any>(`/alerts/${alertId}/acknowledge`, { method: 'POST' }),
  resolveAlert: (alertId: string) =>
    fetchApi<any>(`/alerts/${alertId}/resolve`, { method: 'POST' }),
  triggerEmergency: (data: any) => fetchApi<any>('/alerts/emergency', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Wellness
  logActivity: (data: any) => fetchApi<any>('/wellness/activity', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  logSleep: (data: any) => fetchApi<any>('/wellness/sleep', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  logMood: (data: any) => fetchApi<any>('/wellness/mood', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  logSteps: (data: any) => fetchApi<any>('/wellness/steps', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  getDailySummary: (patientId: string) =>
    fetchApi<any>(`/wellness/${patientId}/daily`),
  getWeeklySummary: (patientId: string) =>
    fetchApi<any>(`/wellness/${patientId}/weekly`),
  getWellnessRecommendations: (patientId: string) =>
    fetchApi<any>(`/wellness/${patientId}/recommendations`),
  getGoals: (patientId: string) =>
    fetchApi<any>(`/wellness/${patientId}/goals`),
  setGoal: (data: any) => fetchApi<any>('/wellness/goals', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // System
  getSystemStatus: () => fetchApi<any>('/dashboard/system/status'),
}
