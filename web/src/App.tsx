import { Navigate, Route, Routes } from 'react-router-dom'
import { RequireAuth } from './auth/RequireAuth'
import { CompanyLayout } from './layout/CompanyLayout'
import { CompanyRedirect } from './pages/CompanyRedirect'
import { HomePage } from './pages/HomePage'
import { LoginPage } from './pages/LoginPage'
import { SectionPage } from './pages/SectionPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/accounts/companies" element={<CompanyRedirect />} />
        <Route path="/accounts/companies/:companyId" element={<CompanyLayout />}>
          <Route index element={<HomePage />} />
          <Route path=":section" element={<SectionPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/accounts/companies" replace />} />
    </Routes>
  )
}
