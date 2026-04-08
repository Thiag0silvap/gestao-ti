import { useCallback, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import api from "../api/api";
import MetricSparkline from "../components/MetricSparkline";
import { useUI } from "../components/UIProvider";
import useAutoRefresh from "../hooks/useAutoRefresh";
import { classifyHostSeverity, severityClassName, severityLabel } from "../utils/hostSeverity";

function ComputerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [computer, setComputer] = useState(null);
  const [assets, setAssets] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [events, setEvents] = useState([]);
  const { notify } = useUI();

  const loadComputerDetails = useCallback(() => {
    api
      .get(`/computers/${id}`)
      .then((response) => setComputer(response.data))
      .catch((error) => {
        console.error(error);
        notify("Erro ao carregar detalhes do computador", "error");
      });

    api
      .get(`/computers/${id}/assets`)
      .then((response) => setAssets(response.data))
      .catch((error) => {
        console.error(error);
        notify("Erro ao carregar ativos do computador", "error");
      });

    api
      .get(`/computers/${id}/metrics?limit=24`)
      .then((response) => setMetrics(response.data))
      .catch((error) => {
        console.error(error);
        notify("Erro ao carregar histórico de métricas", "error");
      });

    api
      .get(`/computers/${id}/events?limit=12`)
      .then((response) => setEvents(response.data))
      .catch((error) => {
        console.error(error);
        notify("Erro ao carregar eventos operacionais", "error");
      });
  }, [id, notify]);

  useAutoRefresh(loadComputerDetails);

  const formatDateTime = (value) => {
    if (!value) return "-";

    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  const hostSeverity = useMemo(() => classifyHostSeverity(computer), [computer]);

  const infoCards = useMemo(() => {
    if (!computer) {
      return [];
    }

    return [
      ["Usuário", computer.user || "-"],
      ["IP", computer.ip_address || "-"],
      ["MAC", computer.mac_address || "-"],
      ["CPU", computer.cpu || "-"],
      ["Uso atual de CPU", computer.cpu_usage_percent != null ? `${computer.cpu_usage_percent}%` : "-"],
      ["RAM", computer.ram || "-"],
      ["Uso atual de memória", computer.memory_usage_percent != null ? `${computer.memory_usage_percent}%` : "-"],
      ["Tipo de memória", computer.memory_type || "-"],
      ["Frequência da memória", computer.memory_speed || "-"],
      ["Disco", computer.disk || "-"],
      ["Disco livre", computer.disk_free_gb != null ? `${computer.disk_free_gb} GB (${computer.disk_free_percent ?? 0}%)` : "-"],
      ["Sistema", computer.os || "-"],
      ["Fabricante", computer.manufacturer || "-"],
      ["Modelo", computer.model || "-"],
      ["Serial Number", computer.serial_number || "-"],
      ["Patrimonio", computer.patrimony_number || "-"],
      ["Uptime", computer.uptime_hours != null ? `${computer.uptime_hours} h` : "-"],
      ["Último contato", formatDateTime(computer.last_seen)],
    ];
  }, [computer]);

  const metricCards = useMemo(() => ([
    {
      title: "CPU",
      value: computer?.cpu_usage_percent != null ? `${computer.cpu_usage_percent}%` : "-",
      values: metrics.map((metric) => metric.cpu_usage_percent).filter((value) => value != null),
      tone: "#0f766e",
    },
    {
      title: "Memória",
      value: computer?.memory_usage_percent != null ? `${computer.memory_usage_percent}%` : "-",
      values: metrics.map((metric) => metric.memory_usage_percent).filter((value) => value != null),
      tone: "#d97706",
    },
    {
      title: "Disco livre",
      value: computer?.disk_free_percent != null ? `${computer.disk_free_percent}%` : "-",
      values: metrics.map((metric) => metric.disk_free_percent).filter((value) => value != null),
      tone: "#2563eb",
    },
  ]), [computer, metrics]);

  if (!computer) {
    return <p className="p-6 text-slate-600">Carregando detalhes...</p>;
  }

  return (
    <div className="space-y-6">
      <section className="section-card overflow-hidden">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Ficha do equipamento
            </p>
            <h2 className="page-title mt-3 text-3xl md:text-[2.8rem]">{computer.hostname}</h2>
            <p className="page-subtitle">
              Dados consolidados enviados pelo agente e complementados pelo inventario interno.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className={severityClassName(hostSeverity)}>
              {severityLabel(hostSeverity)}
            </span>

            <button onClick={() => navigate("/computers")} className="btn-secondary">
              Voltar para lista
            </button>
          </div>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <div className="rounded-[24px] border border-emerald-200 bg-emerald-50 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700">
              Identidade
            </p>
            <p className="mt-3 text-lg font-semibold text-emerald-900">{computer.hostname}</p>
            <p className="mt-1 text-sm text-emerald-800/80">{computer.user || "Sem usuário identificado"}</p>
          </div>

          <div className="rounded-[24px] border border-slate-200 bg-white/85 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Setor</p>
            <p className="mt-3 text-lg font-semibold text-slate-900">{computer.sector || "-"}</p>
            <p className="mt-1 text-sm text-slate-500">{computer.equipment_status || "Sem status"}</p>
          </div>

          <div className="rounded-[24px] border border-amber-200 bg-amber-50 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
              Ativos vinculados
            </p>
            <p className="mt-3 text-lg font-semibold text-amber-900">{assets.length}</p>
            <p className="mt-1 text-sm text-amber-800/80">Itens associados a esta máquina</p>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Telemetria recente
            </p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              Últimas amostras do agente
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Visualize tendência de CPU, memória e espaço livre sem sair da ficha técnica.
          </p>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {metricCards.map((metric) => (
            <div key={metric.title} className="rounded-[24px] border border-slate-200 bg-white/85 p-5">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                {metric.title}
              </p>
              <p className="mt-3 text-3xl font-semibold text-slate-900">{metric.value}</p>
              <div className="mt-4">
                <MetricSparkline values={metric.values} stroke={metric.tone} />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Eventos do host
            </p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              Linha do tempo operacional
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Veja quando o agente sincronizou e quando a severidade mudou.
          </p>
        </div>

        <div className="mt-6 grid gap-4">
          {events.length ? events.map((event) => (
            <div key={event.id} className="rounded-[24px] border border-slate-200 bg-white/85 p-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="text-base font-semibold text-slate-900">{event.title}</p>
                    <span className={
                      event.severity === "critical"
                        ? "status-critical"
                        : event.severity === "warning"
                          ? "status-warning"
                          : event.severity === "offline"
                            ? "status-offline"
                            : "status-neutral"
                    }>
                      {event.severity === "critical"
                        ? "Crítico"
                        : event.severity === "warning"
                          ? "Atenção"
                          : event.severity === "offline"
                            ? "Offline"
                            : "Info"}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{event.message}</p>
                </div>
                <p className="text-sm text-slate-500">{formatDateTime(event.created_at)}</p>
              </div>
            </div>
          )) : (
            <div className="rounded-[24px] border border-slate-200 bg-white/85 p-5 text-sm text-slate-500">
              Nenhum evento operacional registrado ainda.
            </div>
          )}
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {infoCards.map(([label, value]) => (
          <div key={label} className="metric-card">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <h3 className="mt-3 break-words text-lg font-semibold text-slate-900">{value}</h3>
          </div>
        ))}
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Relacao de ativos
            </p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              Itens vinculados
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Utilize esta seção para validar periféricos e rastreabilidade da estação.
          </p>
        </div>

        <div className="mt-6 table-shell">
          {assets.length === 0 ? (
            <div className="px-4 py-10 text-center text-slate-500">Nenhum ativo vinculado.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Patrimonio</th>
                  <th>Fabricante</th>
                  <th>Modelo</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id}>
                    <td>{asset.asset_type}</td>
                    <td>{asset.patrimony_number || "-"}</td>
                    <td>{asset.manufacturer || "-"}</td>
                    <td>{asset.model || "-"}</td>
                    <td>
                      <span className={asset.asset_status === "Ativo" ? "status-online" : "status-neutral"}>
                        {asset.asset_status || "-"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>
    </div>
  );
}

export default ComputerDetail;
