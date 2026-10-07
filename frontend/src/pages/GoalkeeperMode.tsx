import { Navigate, useParams } from 'react-router-dom'

/** Goalkeeper shots now belong to the canonical shot/outcome timeline. */
export default function GoalkeeperMode() {
  const { matchId } = useParams<{ matchId: string }>()
  return <Navigate replace to={`/match/${matchId}/analysis`} />
}
