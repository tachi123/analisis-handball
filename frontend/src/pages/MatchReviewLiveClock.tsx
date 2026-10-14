interface LiveClockProps { seconds: number; running: boolean; onStart: () => void; onPause: () => void; onReset: () => void }

export function LiveClock({ seconds, running, onStart, onPause, onReset }: LiveClockProps) {
  const value = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
  return <section className="rounded border border-indigo-200 bg-indigo-50 p-3" aria-label="Reloj en vivo">
    <p className="text-sm font-medium">Reloj en vivo</p>
    <p className="font-mono text-4xl font-bold">{value}</p>
    <p className="mt-1 text-xs text-indigo-900">{running ? 'El reloj está corriendo.' : 'El reloj está pausado.'} Registrá el saque inicial como 00:00 antes de cargar incidencias.</p>
    <div className="mt-2 flex flex-wrap gap-2"><button className="btn btn-primary" onClick={onStart} disabled={running}>Iniciar</button><button className="btn" onClick={onPause} disabled={!running}>Pausar</button><button className="btn" onClick={onReset} disabled={seconds === 0}>Reiniciar</button></div>
  </section>
}
