import { Navigate, useParams } from 'react-router-dom'

/** Legacy URLs share the persisted video-review workspace; they never create a second clock. */
export default function MatchAnalysis() {
  const { matchId } = useParams<{ matchId: string }>()
  return <Navigate to={`/match/${matchId}/review`} replace />
}
