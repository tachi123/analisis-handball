import { useState } from 'react'
import type { TagState, TagStep } from '../types'
import { INITIAL_TAG_STATE } from '../types'

export function useTagging(teamAction: string) {
  const [state, setState] = useState<TagState>({ ...INITIAL_TAG_STATE, teamAction })

  const reset = () => setState({ ...INITIAL_TAG_STATE, teamAction })

  const go = (patch: Partial<TagState>) =>
    setState(prev => ({ ...prev, ...patch }))

  const selectPlayer = (playerId: number) => go({ playerId, step: 'action' })

  const selectAction = (actionType: string) => {
    if (actionType === 'Lanzamiento') return go({ actionType, step: 'shot_result' })
    if (actionType === 'Pérdida') return go({ actionType, step: 'loss_detail' })
    if (actionType === 'Falta') return go({ actionType, step: 'foul_type' })
    if (actionType === '7 Metros') return go({ actionType, step: 'shot_result' })
    // Timeout / Sustitución → completan directamente
    return go({ actionType, step: 'idle' })
  }

  const selectShotResult = (result: string) => {
    go({ result, step: 'shot_zone' })
  }

  const selectShotZone = (shotZone: string): TagState => {
    const isGoal = state.result === 'Gol' || state.result === 'Gol (Arco Vacío)'
    const nextStep: TagStep = isGoal ? 'assist' : 'idle'
    const next = { ...state, shotZone, step: nextStep }
    setState(next)
    return nextStep === 'idle' ? next : next // only auto-commit when idle
  }

  const selectAssist = (assistPlayerId: number | null): TagState => {
    const next = { ...state, assistPlayerId, step: 'idle' as TagStep }
    setState(next)
    return next
  }

  const selectLossDetail = (lossDetail: string): TagState => {
    const next = { ...state, lossDetail, step: 'idle' as TagStep }
    setState(next)
    return next
  }

  const selectFoulType = (foulType: string) => {
    if (foulType === '+Sanción') return go({ foulType, step: 'sanction_type' })
    const next = { ...state, foulType, step: 'idle' as TagStep }
    setState(next)
    return next
  }

  const selectSanctionType = (sanctionType: string) =>
    go({ sanctionType, step: 'sanction_target' })

  const selectSanctionTarget = (sanctionTarget: string): TagState => {
    const next = { ...state, sanctionTarget, step: 'idle' as TagStep }
    setState(next)
    return next
  }

  // Sustitución: seleccionar jugador que sale → jugador que entra
  const startSubstitution = () => go({ actionType: 'Sustitución', step: 'sub_out' })

  const selectSubOut = (playerId: number) => go({ subOutPlayerId: playerId, step: 'sub_in' })

  const selectSubIn = (playerId: number): TagState => {
    const next = { ...state, subInPlayerId: playerId, step: 'idle' as TagStep }
    setState(next)
    return next
  }

  return {
    state,
    reset,
    selectPlayer,
    selectAction,
    selectShotResult,
    selectShotZone,
    selectAssist,
    selectLossDetail,
    selectFoulType,
    selectSanctionType,
    selectSanctionTarget,
    startSubstitution,
    selectSubOut,
    selectSubIn,
  }
}
