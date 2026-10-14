import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  confirmMatchPDF,
  createAnalysisRun,
  getAnalysisRuns,
  getMatch,
  getOfficialSheet,
  previewMatchPDF,
  saveAnalysisSession,
} from "../api/client";
import type { AnalysisProfile, AnalysisRun, MatchPDFPreviewResult } from "../types";

const player = (
  row: MatchPDFPreviewResult["preview"]["home_team"]["players"][number],
) => ({
  name: row.name,
  jersey_number: row.number,
  official_goals: row.goals,
  official_yellow: row.yellow,
  official_2min: row.two_min,
  official_red: row.red,
  official_blue: row.blue,
});

const hasMismatch = (preview: MatchPDFPreviewResult) =>
  preview.score_reconciliation === "mismatch" ||
  preview.date_reconciliation === "mismatch" ||
  preview.home_compatibility.status === "incompatible" ||
  preview.away_compatibility.status === "incompatible";

export default function ManualMatchPreparationPage() {
  const id = Number(useParams().matchId);
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<MatchPDFPreviewResult | null>(null);
  const [ack, setAck] = useState(false);
  const [mode, setMode] = useState<"video" | "manual" | "live">("video");
  const [pendingRun, setPendingRun] = useState<AnalysisRun | null>(null);
  const match = useQuery({
    queryKey: ["match", id],
    queryFn: () => getMatch(id),
    enabled: Boolean(id),
  });
  const sheet = useQuery({
    queryKey: ["official-sheet", id],
    queryFn: () => getOfficialSheet(id),
    enabled: Boolean(id),
    retry: false,
  });
  const runs = useQuery({
    queryKey: ["analysis-runs", id],
    queryFn: () => getAnalysisRuns(id),
    enabled: Boolean(id) && Boolean(sheet.data),
    retry: false,
  });
  const parse = useMutation({
    mutationFn: () => previewMatchPDF(id, file!),
    onSuccess: setPreview,
  });
  const confirm = useMutation({
    mutationFn: () =>
      confirmMatchPDF(id, file!, {
        home_players: preview!.preview.home_team.players.map(player),
        away_players: preview!.preview.away_team.players.map(player),
        acknowledge_mismatches: ack,
      }),
    onSuccess: () => sheet.refetch(),
  });
  const start = useMutation({
    mutationFn: async () => {
      const retryingPendingRun = pendingRun?.mode === mode;
      const persistedRun = retryingPendingRun
        ? undefined
        : (await runs.refetch()).data?.find(
          (run) => run.match_id === id && run.mode === mode && run.status === "draft",
        );
      if (persistedRun) return persistedRun;
      const run = pendingRun?.mode === mode
        ? pendingRun
        : await createAnalysisRun(id, mode);
      try {
        await saveAnalysisSession(id, {
          mode,
          profile: "complete" as AnalysisProfile,
          source: mode === "video" && match.data?.youtube_link
            ? { url: match.data.youtube_link, availability_state: "unknown" }
            : null,
          video_position_seconds: null,
          clock_start_video_seconds: null,
          angle: null,
          filters: {},
          draft: {},
          queue: [],
          anchors: [],
          time_segments: [],
        }, run.id);
      } catch (error) {
        // Keep the draft so a retry cannot create a second analysis run.
        setPendingRun(run);
        throw error;
      }
      return run;
    },
    onSuccess: (run) => {
      setPendingRun(null);
      navigate(`/match/${id}/review?run=${run.id}`);
    },
  });
  if (match.isLoading) return <main className="p-4">Cargando partido…</main>;
  if (!match.data)
    return (
      <main className="p-4" role="alert">
        No se encontró el partido.
      </main>
    );
  const mismatch = preview ? hasMismatch(preview) : false;
  const sheetMissing =
    sheet.isError &&
    (sheet.error as { response?: { status?: number } }).response?.status ===
      404;
  const startError =
    start.error instanceof Error ? start.error.message : "Intentá nuevamente.";
  const matchingDraft = runs.data?.find(
    (run) => run.match_id === id && run.mode === mode && run.status === "draft",
  );
  return (
    <main className="max-w-4xl mx-auto space-y-4 p-4">
      <Link className="btn" to="/matches">
        Partidos
      </Link>
      <header>
        <h1 className="text-2xl font-bold">Preparar partido manual</h1>
        <p>
          {match.data.home_team?.name} vs {match.data.away_team?.name} ·{" "}
          {match.data.tournament?.name ?? "Sin torneo"}
        </p>
      </header>
      {sheet.isLoading ? (
        <p>Cargando planilla oficial…</p>
      ) : sheet.data ? (
        <>
          <section className="card">
            <h2 className="font-semibold">Planilla oficial confirmada</h2>
            <p>
              {sheet.data.home.name} {sheet.data.home.score} -{" "}
              {sheet.data.away.score} {sheet.data.away.name}
            </p>
          </section>
          <section className="card space-y-3">
            <h2 className="font-semibold">Iniciar análisis</h2>
            <p className="text-sm text-gray-600">Elegí cómo vas a registrar el partido. En Video YouTube vas a cargar o reutilizar el enlace en la revisión.</p>
            <fieldset className="grid gap-2 md:grid-cols-3">
              <legend className="sr-only">Modo de análisis</legend>
              {[
                ["video", "Video YouTube"],
                ["manual", "Video local manual"],
                ["live", "En vivo"],
              ].map(([value, label]) => <label key={value} className={`cursor-pointer rounded border p-3 ${mode === value ? "border-indigo-600 bg-indigo-50" : "bg-white"}`}><input className="mr-2" type="radio" name="mode" value={value} checked={mode === value} onChange={() => setMode(value as "video" | "manual" | "live")} />{label}</label>)}
            </fieldset>
            <button className="btn btn-primary" onClick={() => start.mutate()} disabled={start.isPending}>{start.isPending ? "Iniciando análisis…" : start.isError && pendingRun ? "Reintentar inicio de análisis" : matchingDraft ? "Retomar borrador" : "Crear borrador"}</button>
          </section>
          {start.isError && (
            <p role="alert" className="text-red-700">
              {pendingRun
                ? `El borrador ya fue creado, pero no se pudo guardar la sesión inicial: ${startError} Reintentá para continuar con el mismo borrador.`
                : `No se pudo crear el borrador: ${startError}`}
            </p>
          )}
          {runs.data?.filter((run) => run.status === "draft").map((run) => (
            <section key={run.id} className="card flex flex-wrap items-center justify-between gap-3">
              <p><b>Borrador existente:</b> {run.mode}</p>
              <button className="btn" onClick={() => navigate(`/match/${id}/review?run=${run.id}`)}>Retomar borrador</button>
            </section>
          ))}
          {runs.data?.some((run) => run.status === "active") && <button className="btn" onClick={() => navigate(`/match/${id}/review`)}>Abrir análisis canónico activo</button>}
        </>
      ) : sheet.isError && !sheetMissing ? (
        <section className="card space-y-3" role="alert">
          <p className="text-red-700">
            No se pudo consultar la planilla oficial. Verificá tu acceso o la
            conexión e intentá nuevamente.
          </p>
          <button
            className="btn"
            onClick={() => sheet.refetch()}
            disabled={sheet.isFetching}
          >
            {sheet.isFetching ? "Reintentando…" : "Reintentar"}
          </button>
        </section>
      ) : (
        <section className="card space-y-3">
          <h2 className="font-semibold">Cargar y revisar planilla oficial</h2>
          <input
            aria-label="Archivo PDF"
            type="file"
            accept="application/pdf"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setPreview(null);
            }}
          />
          <button
            className="btn"
            disabled={!file || parse.isPending}
            onClick={() => parse.mutate()}
          >
            Revisar PDF
          </button>
          {parse.isError && (
            <p role="alert" className="text-red-700">
              No se pudo leer la planilla.
            </p>
          )}
          {preview && (
            <>
              <p>
                Planilla: {preview.preview.home_team.name}{" "}
                {preview.preview.match_info.home_score} -{" "}
                {preview.preview.match_info.away_score}{" "}
                {preview.preview.away_team.name}
              </p>
              <ul className="text-sm list-disc pl-5">
                {preview.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
              <p className="text-sm">
                Plantel: {preview.preview.home_team.players.length} local,{" "}
                {preview.preview.away_team.players.length} visitante.
              </p>
              {mismatch && (
                <label>
                  <input
                    type="checkbox"
                    checked={ack}
                    onChange={(e) => setAck(e.target.checked)}
                  />{" "}
                  Reconozco las discrepancias informadas.
                </label>
              )}
              <button
                className="btn btn-primary"
                disabled={confirm.isPending || (mismatch && !ack)}
                onClick={() => confirm.mutate()}
              >
                Confirmar planilla
              </button>
              {confirm.isError && (
                <p role="alert" className="text-red-700">
                  No se pudo confirmar la planilla.
                </p>
              )}
            </>
          )}
        </section>
      )}
    </main>
  );
}
