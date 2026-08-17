type ServiceStatus = "ok" | "error";

interface HealthResponse {
  status: "ok" | "degraded";
  postgres: ServiceStatus;
  redis: ServiceStatus;
}

async function fetchHealth(): Promise<HealthResponse | null> {
  const apiUrl = process.env.API_URL ?? "http://api:8000";

  try {
    const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return response.json() as Promise<HealthResponse>;
  } catch {
    return null;
  }
}

function StatusBadge({ label, status }: { label: string; status: ServiceStatus | "unknown" }) {
  const isOk = status === "ok";
  const colorClass = isOk ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";

  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3">
      <span className="font-medium">{label}</span>
      <span className={`rounded-full px-3 py-1 text-sm font-semibold ${colorClass}`}>
        {status === "unknown" ? "sin respuesta" : status}
      </span>
    </div>
  );
}

export default async function HomePage() {
  const health = await fetchHealth();

  const overallStatus: ServiceStatus | "unknown" = health?.status === "ok" ? "ok" : health ? "error" : "unknown";

  return (
    <main className="mx-auto flex min-h-screen max-w-lg flex-col justify-center gap-6 p-8">
      <div>
        <h1 className="text-2xl font-bold">Copiloto Normativo</h1>
        <p className="mt-1 text-gray-600">Estado del sistema</p>
      </div>

      <StatusBadge label="Sistema" status={overallStatus} />

      {health ? (
        <>
          <StatusBadge label="Postgres" status={health.postgres} />
          <StatusBadge label="Redis" status={health.redis} />
        </>
      ) : (
        <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-800">
          No se pudo conectar con la API.
        </p>
      )}
    </main>
  );
}
