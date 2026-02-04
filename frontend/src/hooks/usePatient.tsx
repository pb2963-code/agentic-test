import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../services/api'

interface Patient {
  patient_id: string
  first_name: string
  last_name: string
  email: string
  date_of_birth: string
  age?: number
  bmi?: number
}

interface PatientContextType {
  patient: Patient | null
  loading: boolean
  error: string | null
  setPatient: (patient: Patient | null) => void
  refreshPatient: () => Promise<void>
}

const PatientContext = createContext<PatientContextType | undefined>(undefined)

export function PatientProvider({ children }: { children: ReactNode }) {
  const [patient, setPatient] = useState<Patient | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshPatient = async () => {
    try {
      setLoading(true)
      const patients = await api.getPatients()
      if (patients.patients && patients.patients.length > 0) {
        setPatient(patients.patients[0])
      }
    } catch (err) {
      setError('Failed to load patient data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshPatient()
  }, [])

  return (
    <PatientContext.Provider value={{ patient, loading, error, setPatient, refreshPatient }}>
      {children}
    </PatientContext.Provider>
  )
}

export function usePatient() {
  const context = useContext(PatientContext)
  if (context === undefined) {
    throw new Error('usePatient must be used within a PatientProvider')
  }
  return context
}
