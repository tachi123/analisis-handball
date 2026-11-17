import type { ResultKind } from './resultStrip'

export const normalizedClub = (name: string) => name.normalize('NFD').replace(/[\u0300-\u036f.\s]/g, '').toLowerCase()
export const isSapa = (name: string) => normalizedClub(name) === 'sapa'

export const percent = (value: number, digits = 0) => `${(value * 100).toFixed(digits).replace('.', ',')}%`
export const tinyPercent = (value: number) => value > 0 && value < 0.001 ? '<0,1%' : percent(value)
export const decimal = (value: number, digits = 1) => value.toFixed(digits).replace('.', ',')
export const signed = (value: number) => value > 0 ? `+${value}` : String(value)

export const formatDate = (value: string | null) => {
  if (!value) return 'Fecha a confirmar'
  const [year, month, day] = value.split('-')
  return year && month && day ? `${day}/${month}/${year}` : value
}

export const formatShortDate = (value: string | null) => {
  if (!value) return 's/f'
  const [, month, day] = value.split('-')
  return month && day ? `${day}/${month}` : value
}

export const resultFromScore = (goalsFor: number, goalsAgainst: number): ResultKind => goalsFor > goalsAgainst ? 'win' : goalsFor === goalsAgainst ? 'draw' : 'loss'

export const resultLabel = (result: ResultKind) => result === 'win' ? 'Ganó' : result === 'draw' ? 'Empató' : result === 'loss' ? 'Perdió' : 'Pendiente'
