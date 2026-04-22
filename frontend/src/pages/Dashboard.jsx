import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/api";
import { useUI } from "../components/UIContext";
import useAutoRefresh from "../hooks/useAutoRefresh";

function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();
  const { notify } = useUI();

  const loadDashboard = useCallback(() => {
    api
      .get("/dashboard/summary")
      .then((response) => setData(response.data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          navigate("/");
        } else {
          notify("Erro ao carregar dashboard", "error");
        }
      });
  }, [navigate, notify]);

  useAutoRefresh(loadDashboard);

  const cards = useMemo(() => {
    if (!data) {
      return [];
    }

    return [
      {
        title: "Computadores",
        value: data.total_computers,
        tone: "text-emerald-700",
        description: "Base total monitorada pelo inventário",
      },
      {
        title: "Online recente",
        value: data.online_recently,
        tone: "text-sky-700",
        description: "Máquinas com contato nos últimos 7 dias",
      },
      {
        title: "Offline",
        value: data.offline_hosts,
        tone: "text-rose-700",
        description: "Equipamentos sem contato nas ultimas 24 horas",
      },
      {
        title: "Ativos cadastrados",
        value: data.total_assets,
        tone: "text-amber-700",
        description: "Itens associados ao parque de TI",
      },
      {
        title: "CPU média",
        value: `${data.average_cpu_usage}%`,
        tone: "text-teal-700",
        description: "Uso médio de CPU nas últimas amostras por host",
      },
      {
        title: "Memória média",
        value: `${data.average_memory_usage}%`,
        tone: "text-orange-700",
        description: "Consumo médio de memória observado recentemente",
      },
      {
        title: "Hosts em atenção",
        value: data.warning_hosts,
        tone: "text-amber-700",
        description: "Máquinas com uso elevado ou espaço em nível de alerta",
      },
      {
        title: "Hosts críticos",
        value: data.critical_hosts,
        tone: "text-rose-700",
        description: "Máquinas com saturação ou disco em nível crítico",
      },
    ];
  }, [data]);

  const assetBreakdown = useMemo(() => {
    if (!data) {
      return [];
    }

    return [
      { label: "Monitores", value: data.monitors },
      { label: "Nobreaks", value: data.nobreaks },
      { label: "Estabilizadores", value: data.stabilizers },
      { label: "Impressoras", value: data.printers },
      { label: "CPU alta", value: data.hosts_with_high_cpu },
      { label: "Disco crítico", value: data.hosts_with_low_disk },
      { label: "Offline", value: data.offline_hosts },
    ];
  }, [data]);

  const agentHealthCards = useMemo(() => {
    if (!data) {
      return [];
    }

    return [
      {
        title: "Fila offline",
        value: data.agent_offline_queue_hosts ?? 0,
        detail: `${data.agent_offline_queue_items ?? 0} item(ns) aguardando reenvio`,
        tone: "text-amber-800",
        className: "border-amber-200 bg-amber-50/90",
      },
      {
        title: "Agentes com falha",
        value: data.agent_failure_hosts ?? 0,
        detail: "Máquinas com erro ou falhas consecutivas no agente",
        tone: "text-rose-800",
        className: "border-rose-200 bg-rose-50/90",
      },
      {
        title: "Atualizando",
        value: data.agent_updating_hosts ?? 0,
        detail: "Agentes executando troca remota de versao",
        tone: "text-sky-800",
        className: "border-sky-200 bg-sky-50/90",
      },
      {
        title: "Sem telemetria",
        value: data.agent_without_telemetry ?? 0,
        detail: "Máquinas que ainda não enviaram dados do agente novo",
        tone: "text-slate-800",
        className: "border-slate-200 bg-slate-50/90",
      },
    ];
  }, [data]);

  const formatDateTime = (value) => {
    if (!value) return "-";
    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  if (!data) {
    return <p className="px-2 py-10 text-slate-600">Carregando visão operacional...</p>;
  }

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <div className="section-card overflow-hidden">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
            Panorama da operação
          </p>
          <h2 className="mt-3 page-title max-w-3xl">
            Seu ambiente de TI está visível em tempo real.
          </h2>
          <p className="page-subtitle">
            Use este painel para identificar máquinas ativas, pontos de atenção no inventário
            e a distribuição dos ativos que sustentam a operação.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => (
              <div key={card.title} className="metric-card">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  {card.title}
                </p>
                <p className={`mt-4 text-4xl font-semibold ${card.tone}`}>{card.value}</p>
                <p className="mt-3 max-w-xs text-sm leading-6 text-slate-600">{card.description}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="section-card bg-[linear-gradient(180deg,rgba(24,49,43,0.96)_0%,rgba(20,32,29,0.94)_100%)] text-white">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-100/60">
            Leitura rápida
          </p>
          <h3 className="mt-3 text-[1.9rem] font-semibold">
            Distribuição dos ativos
          </h3>
          <div className="mt-8 space-y-4">
            {assetBreakdown.map((item) => (
              <div key={item.label} className="rounded-[22px] border border-white/10 bg-white/5 px-4 py-4">
                <div className="flex items-center justify-between gap-4">
                  <span className="text-sm uppercase tracking-[0.16em] text-white/60">{item.label}</span>
                  <span className="text-2xl font-semibold text-emerald-100">{item.value}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
        <div className="section-card">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Recomendações de uso
          </p>
          <div className="mt-5 space-y-4">
            {[
              "Priorize a revisão dos equipamentos marcados como offline para confirmar rede, energia ou troca de usuário.",
              "Mantenha os ativos vinculados aos computadores para facilitar atendimento e rastreabilidade.",
              "Use os chamados com computador identificado para acelerar diagnóstico e histórico técnico.",
            ].map((text) => (
              <div key={text} className="rounded-[22px] border border-slate-200/80 bg-white/70 px-4 py-4 text-sm leading-6 text-slate-700">
                {text}
              </div>
            ))}
          </div>
        </div>

        <div className="section-card">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Saúde do inventário
          </p>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <div className="rounded-[24px] border border-emerald-200 bg-emerald-50/90 p-5">
              <p className="text-sm font-semibold text-emerald-800">Cobertura recente</p>
              <p className="mt-2 text-3xl font-semibold text-emerald-900">
                {data.total_computers > 0
                  ? `${Math.round((data.online_recently / data.total_computers) * 100)}%`
                  : "0%"}
              </p>
              <p className="mt-2 text-sm text-emerald-800/80">
                Proporção de máquinas que reportaram atividade dentro da janela recente.
              </p>
            </div>

            <div className="rounded-[24px] border border-amber-200 bg-amber-50/90 p-5">
              <p className="text-sm font-semibold text-amber-800">Itens por computador</p>
              <p className="mt-2 text-3xl font-semibold text-amber-900">
                {data.total_computers > 0 ? (data.total_assets / data.total_computers).toFixed(1) : "0.0"}
              </p>
              <p className="mt-2 text-sm text-amber-800/80">
                Média de ativos cadastrados por máquina inventariada.
              </p>
            </div>

            {agentHealthCards.map((card) => (
              <div key={card.title} className={`rounded-[24px] border p-5 ${card.className}`}>
                <p className={`text-sm font-semibold ${card.tone}`}>{card.title}</p>
                <p className={`mt-2 text-3xl font-semibold ${card.tone}`}>
                  {card.value}
                </p>
                <p className="mt-2 text-sm text-slate-600">
                  {card.detail}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Prioridades operacionais
            </p>
            <h3 className="mt-2 text-[1.85rem] font-semibold text-slate-900">
              Hosts que pedem atenção
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Criticidade calculada por telemetria atual e tempo sem resposta.
          </p>
        </div>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {data.top_risky_hosts?.length ? data.top_risky_hosts.map((host) => (
            <div key={host.id} className="rounded-[24px] border border-slate-200 bg-white/85 p-5">
              <div className="flex items-start justify-between gap-3">
                <p className="text-lg font-semibold text-slate-900">{host.hostname}</p>
                <span className={
                  host.severity === "critical"
                    ? "status-critical"
                    : host.severity === "warning"
                      ? "status-warning"
                      : "status-offline"
                }>
                  {host.severity === "critical" ? "Crítico" : host.severity === "warning" ? "Atenção" : "Offline"}
                </span>
              </div>
              <div className="mt-4 space-y-2 text-sm text-slate-600">
                <p>CPU: {host.cpu_usage_percent != null ? `${host.cpu_usage_percent}%` : "-"}</p>
                <p>Memória: {host.memory_usage_percent != null ? `${host.memory_usage_percent}%` : "-"}</p>
                <p>Disco livre: {host.disk_free_percent != null ? `${host.disk_free_percent}%` : "-"}</p>
              </div>
            </div>
          )) : (
            <div className="rounded-[24px] border border-slate-200 bg-white/85 p-5 text-sm text-slate-500 sm:col-span-2 xl:col-span-3">
              Nenhum host em estado de alerta neste momento.
            </div>
          )}
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Eventos recentes
            </p>
            <h3 className="mt-2 text-[1.85rem] font-semibold text-slate-900">
              O que mudou no ambiente
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Linha do tempo das últimas sincronizações e mudanças de severidade.
          </p>
        </div>

        <div className="mt-6 grid gap-4">
          {data.recent_events?.length ? data.recent_events.map((event) => (
            <div key={event.id} className="rounded-[24px] border border-slate-200 bg-white/85 p-5">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="text-lg font-semibold text-slate-900">{event.hostname}</p>
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
                  <p className="mt-3 text-base font-medium text-slate-800">{event.title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{event.message}</p>
                </div>
                <p className="text-sm text-slate-500">{formatDateTime(event.created_at)}</p>
              </div>
            </div>
          )) : (
            <div className="rounded-[24px] border border-slate-200 bg-white/85 p-5 text-sm text-slate-500">
              Ainda não há eventos operacionais registrados.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

export default Dashboard;
