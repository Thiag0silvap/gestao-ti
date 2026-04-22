import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import api from "../api/api";
import { useUI } from "../components/UIContext";
import useAutoRefresh from "../hooks/useAutoRefresh";
import { severityClassName, severityLabel } from "../utils/hostSeverity";

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [severityFilter, setSeverityFilter] = useState("");
  const [search, setSearch] = useState("");
  const navigate = useNavigate();
  const { notify } = useUI();

  const loadAlerts = useCallback(() => {
    api
      .get("/alerts/active")
      .then((response) => setAlerts(response.data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          navigate("/");
        } else {
          notify("Erro ao carregar alertas ativos", "error");
        }
      });
  }, [navigate, notify]);

  useAutoRefresh(loadAlerts, { intervalMs: 15000 });

  const filteredAlerts = useMemo(() => (
    alerts.filter((alert) => {
      const searchText = search.toLowerCase();
      const matchesSearch =
        alert.hostname?.toLowerCase().includes(searchText) ||
        alert.title?.toLowerCase().includes(searchText) ||
        alert.message?.toLowerCase().includes(searchText) ||
        alert.metric?.toLowerCase().includes(searchText);

      const matchesSeverity = !severityFilter || alert.severity === severityFilter;
      return matchesSearch && matchesSeverity;
    })
  ), [alerts, search, severityFilter]);

  const totals = useMemo(() => (
    filteredAlerts.reduce((summary, alert) => {
      summary[alert.severity] += 1;
      return summary;
    }, { critical: 0, warning: 0, offline: 0 })
  ), [filteredAlerts]);

  const formatDateTime = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <div className="section-card">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Alertas ativos
          </p>
          <h2 className="page-title mt-3 max-w-3xl">
            Priorize o que virou risco operacional antes que vire incidente.
          </h2>
          <p className="page-subtitle">
            Alertas calculados a partir da telemetria mais recente de cada host.
          </p>
        </div>

        <div className="section-card">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Críticos</p>
              <p className="mt-3 text-3xl font-semibold text-rose-700">{totals.critical}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Atenção</p>
              <p className="mt-3 text-3xl font-semibold text-amber-700">{totals.warning}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Offline</p>
              <p className="mt-3 text-3xl font-semibold text-slate-700">{totals.offline}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <input
            type="text"
            placeholder="Buscar por host, métrica ou descrição"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="field-input"
          />

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="field-input"
          >
            <option value="">Todas as severidades</option>
            <option value="critical">Crítico</option>
            <option value="warning">Atenção</option>
            <option value="offline">Offline</option>
          </select>

          <button
            type="button"
            onClick={() => {
              setSearch("");
              setSeverityFilter("");
            }}
            className="btn-secondary"
          >
            Limpar filtros
          </button>
        </div>
      </section>

      <section className="grid gap-4">
        {filteredAlerts.length ? filteredAlerts.map((alert, index) => (
          <div key={`${alert.computer_id}-${alert.metric}-${index}`} className="section-card">
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div>
                <div className="flex flex-wrap items-center gap-3">
                  <Link to={`/computers/${alert.computer_id}`} className="text-xl font-semibold text-slate-900 hover:text-emerald-700">
                    {alert.hostname}
                  </Link>
                  <span className={severityClassName(alert.severity)}>
                    {severityLabel(alert.severity)}
                  </span>
                </div>
                <p className="mt-3 text-base font-medium text-slate-800">{alert.title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{alert.message}</p>
              </div>

              <div className="min-w-[220px] rounded-[20px] border border-slate-200 bg-white/80 p-4 text-sm text-slate-600">
                <p>Setor: {alert.sector || "-"}</p>
                <p className="mt-1">Último contato: {formatDateTime(alert.last_seen)}</p>
                <p className="mt-1">CPU: {alert.cpu_usage_percent != null ? `${alert.cpu_usage_percent}%` : "-"}</p>
                <p className="mt-1">Memória: {alert.memory_usage_percent != null ? `${alert.memory_usage_percent}%` : "-"}</p>
                <p className="mt-1">Disco livre: {alert.disk_free_percent != null ? `${alert.disk_free_percent}%` : "-"}</p>
              </div>
            </div>
          </div>
        )) : (
          <div className="section-card text-sm text-slate-500">
            Nenhum alerta ativo com os filtros atuais.
          </div>
        )}
      </section>
    </div>
  );
}

export default Alerts;
