import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import MatchesPage from './pages/MatchesPage'
import TournamentsPage from './pages/TournamentsPage'
import TeamsPage from './pages/TeamsPage'
import PlayersPage from './pages/PlayersPage'
import MatchLive from './pages/MatchLive'
import StatisticsPage from './pages/StatisticsPage'
import SquadPage from './pages/SquadPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Full-screen live analysis (no nav) */}
      <Route path="/match/:matchId/live" element={<ProtectedRoute><MatchLive /></ProtectedRoute>} />
      <Route path="/match/:matchId/stats" element={<ProtectedRoute><StatisticsPage /></ProtectedRoute>} />
      <Route path="/match/:matchId/squad" element={<ProtectedRoute><SquadPage /></ProtectedRoute>} />

      {/* Main layout with bottom nav */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/matches" element={<MatchesPage />} />
        <Route path="/tournaments" element={<TournamentsPage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/players" element={<PlayersPage />} />
        <Route path="*" element={<Navigate to="/matches" replace />} />
      </Route>
    </Routes>
  )
}
