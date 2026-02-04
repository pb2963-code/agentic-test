import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { Vitals } from './pages/Vitals'
import { Medications } from './pages/Medications'
import { Symptoms } from './pages/Symptoms'
import { Wellness } from './pages/Wellness'
import { Alerts } from './pages/Alerts'
import { PatientProvider } from './hooks/usePatient'

function App() {
  return (
    <PatientProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="vitals" element={<Vitals />} />
            <Route path="medications" element={<Medications />} />
            <Route path="symptoms" element={<Symptoms />} />
            <Route path="wellness" element={<Wellness />} />
            <Route path="alerts" element={<Alerts />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </PatientProvider>
  )
}

export default App
