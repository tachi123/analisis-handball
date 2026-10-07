type Props = {
  zones: Record<string, number>
  coverage: { recorded: number; missing_zone: number; goalkeeper_unknown: number; excluded: number; unknown: number; clock_unverified: number }
}

export default function ShotZoneHeatmap({ zones, coverage }: Props) {
  return <section className="card" aria-labelledby="shot-zone-heading">
    <h2 id="shot-zone-heading" className="font-semibold">Mapa de tiros IHF</h2>
    <p className="text-sm text-gray-600">Solo cubetas entregadas por el servidor; las zonas faltantes no se asignan.</p>
    <div className="mt-2 grid grid-cols-3 gap-1" role="grid" aria-label="Mapa de zonas IHF">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9].map(zone => <div key={zone} role="gridcell" aria-label={`Zona IHF ${zone}: ${zones[String(zone)] ?? 0} tiros`} className="min-h-14 rounded bg-indigo-50 p-2 text-center"><b>{zone}</b><span className="block text-lg">{zones[String(zone)] ?? 0}</span></div>)}
    </div>
    <dl className="mt-3 grid grid-cols-2 gap-2 text-sm">
      <div><dt className="font-medium">Con zona</dt><dd>{coverage.recorded}</dd></div><div><dt className="font-medium">Sin zona</dt><dd>{coverage.missing_zone}</dd></div>
      <div><dt className="font-medium">Arquero desconocido</dt><dd>{coverage.goalkeeper_unknown}</dd></div><div><dt className="font-medium">Reloj sin verificar</dt><dd>{coverage.clock_unverified}</dd></div>
      <div><dt className="font-medium">Excluidos</dt><dd>{coverage.excluded}</dd></div><div><dt className="font-medium">Desconocidos</dt><dd>{coverage.unknown}</dd></div>
    </dl>
  </section>
}
