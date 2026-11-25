import { readFileSync } from 'node:fs'
import { renderToString } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { decodePublicCompetition, decodePublicForecast, decodePublicTournamentCatalog } from './publicCompetitions'
import { Competitions } from './Competitions'
import { CompetitionDetail } from './CompetitionDetail'
import { Forecast } from './Forecast'
import { SeasonProfile } from './SeasonProfile'

const read = (name: string) => JSON.parse(readFileSync(new URL(`../public/${name}`, import.meta.url), 'utf-8'))
const noop = () => undefined

describe('public competition views render with the shipped artifacts', () => {
  const catalog = decodePublicTournamentCatalog(read('tournaments.json'))
  const permanencia = decodePublicCompetition(read('tournament_permanencia-2026.json'))
  const aperturaB = decodePublicCompetition(read('tournament_apertura-zona-b-2026.json'))
  const forecast = decodePublicForecast(read('forecast_permanencia-2026.json'))

  it('renders the catalog', () => {
    const html = renderToString(<Competitions catalog={catalog} onOpen={noop} onForecast={noop} onHome={noop} />)
    expect(html).toContain('Torneos')
    expect(html).toContain('Permanencia 2026')
    expect(html).toContain('SAPA')
  })

  it('renders a tournament detail with standings and marks', () => {
    const html = renderToString(<CompetitionDetail competition={permanencia} onBack={noop} onHome={noop} onForecast={noop} onSeason={noop} />)
    expect(html).toContain('Tabla de posiciones')
    expect(html).toContain('Lanús C')
    expect(html).toContain('Rachas y extremos')
    expect(html.indexOf('Rachas y extremos')).toBeLessThan(html.indexOf('Tabla de posiciones'))
  })

  it('renders the completed closing view with its preserved pre-match appendix', () => {
    const html = renderToString(<Forecast forecast={forecast} tournament={permanencia} onBack={noop} onHome={noop} onTournament={noop} onSeason={noop} />)
    expect(html).toContain('Cierre')
    expect(html).toContain('confirmado')
    expect(html).toContain('Anexo reutilizable')
    expect(html).toContain('Resultado final confirmado')
    expect(html).toContain('S.A.P.A.')
    expect(html).toContain('Pronóstico personal de la convocatoria')
  })

  it('renders the full annual profile with every match', () => {
    const html = renderToString(<SeasonProfile club="Lanús C" competitions={[aperturaB, permanencia]} forecast={forecast} onBack={noop} onHome={noop} onForecast={noop} onTournament={noop} />)
    expect(html).toContain('Lanús C')
    expect(html).toContain('El año completo, fecha por fecha')
    expect(html).toContain('Goleadores del año')
    expect(html).toContain('Continuidad')
    expect(html).toContain('Composición del ataque')
    expect(html).toContain('Barreto')
    expect(html).toContain('15,5%')
    expect(html).toContain('F1')
    expect(html).toContain('F15')
  })
})
