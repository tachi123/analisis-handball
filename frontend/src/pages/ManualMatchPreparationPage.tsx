import { useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  confirmMatchPDF,
  enableCanonicalAnalysis,
  getMatch,
  getOfficialSheet,
  previewMatchPDF,
  saveAnalysisSession,
} from "../api/client";
import type { MatchPDFPreviewResult } from "../types";

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
  const [canonicalEnabled, setCanonicalEnabled] = useState(false);
  const canonicalEnabledRef = useRef(false);
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
      if (!canonicalEnabledRef.current) {
        await enableCanonicalAnalysis(id);
        canonicalEnabledRef.current = true;
        setCanonicalEnabled(true);
      }
      return saveAnalysisSession(id, {
        mode: "video",
        profile: "complete",
        source: null,
        video_position_seconds: null,
        clock_start_video_seconds: null,
        angle: null,
        filters: {},
        draft: {},
        queue: [],
        anchors: [],
        time_segments: [],
      });
    },
    onSuccess: () => navigate(`/match/${id}/review`),
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
          <button
            className="btn btn-primary"
            onClick={() => start.mutate()}
            disabled={start.isPending}
          >
            {start.isError && canonicalEnabled
              ? "Reintentar inicio de análisis"
              : "Iniciar análisis de video"}
          </button>
          {start.isError && (
            <p role="alert" className="text-red-700">
              {canonicalEnabled
                ? `El análisis canónico ya fue habilitado, pero no se pudo guardar la sesión inicial: ${startError} Reintentá para crear la sesión. La habilitación no se revirtió.`
                : `No se pudo habilitar el análisis canónico: ${startError}`}
            </p>
          )}
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
