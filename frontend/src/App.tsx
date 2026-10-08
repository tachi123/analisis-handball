import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import MatchesPage from './pages/MatchesPage'
import TournamentsPage from './pages/TournamentsPage'
import TeamsPage from './pages/TeamsPage'
import PlayersPage from './pages/PlayersPage'
import MatchLive from './pages/MatchLive'
import MatchAnalysis from './pages/MatchAnalysis'
import StatisticsPage from './pages/StatisticsPage'
import SquadPage from './pages/SquadPage'
import GoalkeeperMode from './pages/GoalkeeperMode'
import MatchReview from './pages/MatchReview'
import MatchReportsTimeline from './pages/MatchReportsTimeline'
import GoalkeeperPanel from './pages/GoalkeeperPanel'
import FixtureRosterPage from './pages/FixtureRosterPage'
import FixtureReviewPage from './pages/FixtureReviewPage'
import FixturePreparationPage from './pages/FixturePreparationPage'
import ManualMatchPreparationPage from './pages/ManualMatchPreparationPage'
import DashboardPage from './pages/DashboardPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Full-screen live analysis (no nav) */}
      <Route path="/match/:matchId/live" element={<ProtectedRoute><MatchLive /></ProtectedRoute>} />
      <Route path="/match/:matchId/analysis" element={<ProtectedRoute><MatchAnalysis /></ProtectedRoute>} />
      <Route path="/match/:matchId/stats" element={<ProtectedRoute><StatisticsPage /></ProtectedRoute>} />
      <Route path="/match/:matchId/squad" element={<ProtectedRoute><SquadPage /></ProtectedRoute>} />
      <Route path="/match/:matchId/goalkeeper" element={<ProtectedRoute><GoalkeeperMode /></ProtectedRoute>} />
       <Route path="/match/:matchId/review" element={<ProtectedRoute><MatchReview /></ProtectedRoute>} />
        <Route path="/match/:matchId/timeline" element={<ProtectedRoute><MatchReportsTimeline /></ProtectedRoute>} />
        <Route path="/match/:matchId/goalkeeper-panel" element={<ProtectedRoute><GoalkeeperPanel /></ProtectedRoute>} />
        <Route path="/match/:matchId/reports" element={<ProtectedRoute><Navigate to="../timeline" relative="path" replace /></ProtectedRoute>} />

      {/* Main layout with bottom nav */}
      <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route path="/matches" element={<MatchesPage />} />
        <Route path="/matches/:matchId/prepare" element={<ManualMatchPreparationPage />} />
         <Route path="/fixtures/:fixtureKey/review" element={<FixtureReviewPage />} />
         <Route path="/fixtures/:fixtureKey" element={<FixturePreparationPage />} />
        <Route path="/fixtures/:fixtureKey/roster" element={<FixtureRosterPage />} />
        <Route path="/tournaments" element={<TournamentsPage />} />
        <Route path="/teams" element={<TeamsPage />} />
        <Route path="/players" element={<PlayersPage />} />
        <Route path="/match/:matchId/dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/matches" replace />} />
      </Route>
    </Routes>
  )
}
