import { useCallback, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import api from "../api/api";
import MetricSparkline from "../components/MetricSparkline";
import { useUI } from "../components/UIContext";
import useAutoRefresh from "../hooks/useAutoRefresh";
import { getStoredUser } from "../services/sessionService";
import { classifyHostSeverity, severityClassName, severityLabel } from "../utils/hostSeverity";

const REMOTE_ACTION_LABELS = {
  restart: "Reiniciar",
  shutdown: "Desligar",
  logoff: "Fazer logoff",
  lock: "Bloquear sessão",
  update_agent: "Atualizar agente",
};

function ComputerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [computer, setComputer] = useState(null);
  const [assets, setAssets] = useState([]);
  const [printers, setPrinters] = useState([]);
  const [metrics, setMetrics] = useState([]);
  const [events, setEvents] = useState([]);
  const [remoteActions, setRemoteActions] = useState([]);
  const [remoteActionLoading, setRemoteActionLoading] = useState(null);
  const { notify, confirm, prompt } = useUI();
  const currentUser = useMemo(() => getStoredUser(), []);
  const canManageRemoteActions = currentUser && ["admin", "technician"].includes(currentUser.role);

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
      .get(`/computers/${id}/printers`)
      .then((response) => setPrinters(response.data))
      .catch((error) => {
        console.error(error);
        notify("Erro ao carregar impressoras do computador", "error");
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

    if (canManageRemoteActions) {
      api
        .get(`/computers/${id}/remote-actions?limit=10`)
        .then((response) => setRemoteActions(response.data))
        .catch((error) => {
          console.error(error);
          notify("Erro ao carregar a fila de acoes remotas", "error");
        });
    } else {
      setRemoteActions([]);
    }
  }, [canManageRemoteActions, id, notify]);

  useAutoRefresh(loadComputerDetails);

  const formatDateTime = (value) => {
    if (!value) return "-";

    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  const hostSeverity = useMemo(() => classifyHostSeverity(computer), [computer]);
  const agentOperationalState = useMemo(() => {
    if (!computer) {
      return {
        tone: "warning",
        label: "Sem dados do agente",
        summary: "Nenhuma telemetria operacional do agente foi recebida ainda.",
      };
    }

    if ((computer.agent_offline_queue_size ?? 0) > 0) {
      return {
        tone: "warning",
        label: "Fila offline pendente",
        summary: `${computer.agent_offline_queue_size} item(ns) aguardando reenvio para a API.`,
      };
    }

    if ((computer.agent_consecutive_failures ?? 0) > 0 || computer.agent_last_error_message) {
      return {
        tone: "critical",
        label: "Agente com falhas recentes",
        summary: computer.agent_last_error_message || "O agente registrou erro recente de sincronização.",
      };
    }

    if ((computer.agent_state || "").toLowerCase() === "updating") {
      return {
        tone: "warning",
        label: "Agente em atualização",
        summary: "O agente está executando o fluxo de atualização remota.",
      };
    }

    return {
      tone: "healthy",
      label: "Agente operacional",
      summary: "Sincronização recente sem fila offline e sem falhas acumuladas.",
    };
  }, [computer]);
  const activeRemoteAction = useMemo(
    () => remoteActions.find((action) => action.status === "pending" || action.status === "running") || null,
    [remoteActions],
  );

  const formatRemoteActionStatus = (status) => {
    const map = {
      pending: "Pendente",
      running: "Executando",
      success: "Concluida",
      failed: "Falhou",
      expired: "Expirada",
      cancelled: "Cancelada",
    };
    return map[status] || status || "-";
  };

  const remoteActionStatusClass = (status) => {
    if (status === "success") return "status-online";
    if (status === "failed") return "status-critical";
    if (status === "running") return "status-warning";
    if (status === "expired" || status === "cancelled") return "status-offline";
    return "status-neutral";
  };

  const triggerRemoteAction = async (actionType) => {
    if (!computer || !canManageRemoteActions) {
      return;
    }

    if (activeRemoteAction) {
      notify("Já existe uma ação remota pendente ou em execução para esta máquina.", "error");
      return;
    }

    const justification = await prompt({
      title: `Justifique ${REMOTE_ACTION_LABELS[actionType].toLowerCase()}`,
      message: "Informe por que essa ação precisa ser enviada para o computador.",
      confirmLabel: "Avancar",
      cancelLabel: "Cancelar",
      placeholder: "Ex.: manutencao agendada, host travado, apoio ao colaborador...",
    });

    if (!justification) {
      return;
    }

    const confirmed = await confirm({
      title: `${REMOTE_ACTION_LABELS[actionType]} ${computer.hostname}?`,
      message: `Essa ação será enviada ao agente e executada na próxima sincronização da máquina.\n\nJustificativa: ${justification}`,
      confirmLabel: "Enviar ação",
      cancelLabel: "Cancelar",
      tone: actionType === "shutdown" || actionType === "restart" ? "danger" : "default",
    });

    if (!confirmed) {
      return;
    }

    setRemoteActionLoading(actionType);
    try {
      await api.post(`/computers/${id}/remote-actions`, {
        action_type: actionType,
        justification,
      });
      notify("Acao remota enviada para a fila do agente.", "success");
      loadComputerDetails();
    } catch (error) {
      console.error(error);
      notify("Não foi possível enviar a ação remota.", "error");
    } finally {
      setRemoteActionLoading(null);
    }
  };

  const cancelRemoteAction = async (action) => {
    if (!computer || !canManageRemoteActions || action.status !== "pending") {
      return;
    }

    const confirmed = await confirm({
      title: `Cancelar ${REMOTE_ACTION_LABELS[action.action_type]?.toLowerCase() || action.action_type}?`,
      message: "A ação ainda não foi executada pelo agente. Deseja remover da fila?",
      confirmLabel: "Cancelar ação",
      cancelLabel: "Voltar",
      tone: "danger",
    });

    if (!confirmed) {
      return;
    }

    setRemoteActionLoading(`cancel-${action.id}`);
    try {
      await api.post(`/computers/${id}/remote-actions/${action.id}/cancel`);
      notify("Acao remota cancelada com sucesso.", "success");
      loadComputerDetails();
    } catch (error) {
      console.error(error);
      notify("Não foi possível cancelar a ação remota.", "error");
    } finally {
      setRemoteActionLoading(null);
    }
  };

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
      ["Agent ID", computer.agent_id || "-"],
      ["Estado do agente", computer.agent_state || "-"],
      ["Versao do agente", computer.agent_version || "-"],
      ["Agente iniciado em", formatDateTime(computer.agent_started_at)],
      ["Ultima tentativa do agente", formatDateTime(computer.agent_last_attempt_at)],
      ["Ultimo sucesso do agente", formatDateTime(computer.agent_last_success_at)],
      ["Ultimo erro do agente", computer.agent_last_error_message || "-"],
      ["Horario do ultimo erro", formatDateTime(computer.agent_last_error_at)],
      ["Falhas consecutivas", computer.agent_consecutive_failures != null ? String(computer.agent_consecutive_failures) : "-"],
      ["Fila offline pendente", computer.agent_offline_queue_size != null ? String(computer.agent_offline_queue_size) : "-"],
      ["Ultima coleta do agente", formatDateTime(computer.collected_at)],
      ["Tentativa atual de sync", computer.sync_attempt != null ? String(computer.sync_attempt) : "-"],
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

        <div className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
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

          <div className="rounded-[24px] border border-sky-200 bg-sky-50 p-5">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700">
              Impressoras
            </p>
            <p className="mt-3 text-lg font-semibold text-sky-900">{printers.length}</p>
            <p className="mt-1 text-sm text-sky-800/80">Filas detectadas pelo agente local</p>
          </div>
        </div>

        <div
          className={
            agentOperationalState.tone === "critical"
              ? "mt-4 rounded-[24px] border border-red-200 bg-red-50 p-5"
              : agentOperationalState.tone === "warning"
                ? "mt-4 rounded-[24px] border border-amber-200 bg-amber-50 p-5"
                : "mt-4 rounded-[24px] border border-emerald-200 bg-emerald-50 p-5"
          }
        >
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <p
                className={
                  agentOperationalState.tone === "critical"
                    ? "text-xs font-semibold uppercase tracking-[0.16em] text-red-700"
                    : agentOperationalState.tone === "warning"
                      ? "text-xs font-semibold uppercase tracking-[0.16em] text-amber-700"
                      : "text-xs font-semibold uppercase tracking-[0.16em] text-emerald-700"
                }
              >
                Estado operacional do agente
              </p>
              <p
                className={
                  agentOperationalState.tone === "critical"
                    ? "mt-3 text-lg font-semibold text-red-900"
                    : agentOperationalState.tone === "warning"
                      ? "mt-3 text-lg font-semibold text-amber-900"
                      : "mt-3 text-lg font-semibold text-emerald-900"
                }
              >
                {agentOperationalState.label}
              </p>
              <p
                className={
                  agentOperationalState.tone === "critical"
                    ? "mt-1 text-sm text-red-800/80"
                    : agentOperationalState.tone === "warning"
                      ? "mt-1 text-sm text-amber-800/80"
                      : "mt-1 text-sm text-emerald-800/80"
                }
              >
                {agentOperationalState.summary}
              </p>
            </div>

            <span
              className={severityClassName(
                agentOperationalState.tone === "healthy"
                  ? "healthy"
                  : agentOperationalState.tone === "critical"
                    ? "critical"
                    : "warning",
              )}
            >
              {agentOperationalState.tone === "healthy"
                ? "Operacional"
                : agentOperationalState.tone === "critical"
                  ? "Falha"
                  : "Atencao"}
            </span>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Comandos remotos
            </p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              Controle operacional
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Ações seguras e auditadas executadas pelo agente local da máquina.
          </p>
        </div>

        {canManageRemoteActions ? (
          <>
            {activeRemoteAction && (
              <div className="mt-6 rounded-[24px] border border-amber-200 bg-amber-50 p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
                  Acao ativa
                </p>
                <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div>
                    <p className="text-lg font-semibold text-amber-900">
                      {REMOTE_ACTION_LABELS[activeRemoteAction.action_type] || activeRemoteAction.action_type}
                    </p>
                    <p className="mt-1 text-sm leading-6 text-amber-900/80">
                      {formatRemoteActionStatus(activeRemoteAction.status)}.
                      {activeRemoteAction.justification ? ` ${activeRemoteAction.justification}` : ""}
                    </p>
                  </div>
                  {activeRemoteAction.status === "pending" && (
                    <button
                      type="button"
                      onClick={() => cancelRemoteAction(activeRemoteAction)}
                      className="btn-danger"
                      disabled={remoteActionLoading === `cancel-${activeRemoteAction.id}`}
                    >
                      {remoteActionLoading === `cancel-${activeRemoteAction.id}` ? "Cancelando..." : "Cancelar pendente"}
                    </button>
                  )}
                </div>
              </div>
            )}

            <div className="mt-6 flex flex-wrap gap-3">
              {Object.entries(REMOTE_ACTION_LABELS).map(([actionType, label]) => (
                <button
                  key={actionType}
                  type="button"
                  onClick={() => triggerRemoteAction(actionType)}
                  className={actionType === "shutdown" || actionType === "restart" ? "btn-danger" : "btn-secondary"}
                  disabled={remoteActionLoading === actionType || Boolean(activeRemoteAction)}
                >
                  {remoteActionLoading === actionType ? "Enviando..." : label}
                </button>
              ))}
            </div>

            <div className="mt-6 grid gap-4">
              {remoteActions.length ? remoteActions.map((action) => (
                <div key={action.id} className="rounded-[24px] border border-slate-200 bg-white/85 p-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <div className="flex flex-wrap items-center gap-3">
                        <p className="text-base font-semibold text-slate-900">
                          {REMOTE_ACTION_LABELS[action.action_type] || action.action_type}
                        </p>
                        <span className={remoteActionStatusClass(action.status)}>
                          {formatRemoteActionStatus(action.status)}
                        </span>
                      </div>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        Solicitado por {action.requested_by || "-"}.
                        {action.source_ip ? ` Origem: ${action.source_ip}.` : ""}
                        {action.justification ? ` ${action.justification}` : ""}
                        {action.result_message ? ` Resultado: ${action.result_message}` : ""}
                      </p>
                    </div>
                    <p className="text-sm text-slate-500">{formatDateTime(action.created_at)}</p>
                  </div>
                </div>
              )) : (
                <div className="rounded-[24px] border border-slate-200 bg-white/85 p-5 text-sm text-slate-500">
                  Nenhuma ação remota registrada para este host.
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="mt-6 rounded-[24px] border border-slate-200 bg-white/85 p-5 text-sm text-slate-500">
            Seu perfil não possui permissão para enviar comandos remotos.
          </div>
        )}
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
              Impressoras detectadas
            </p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              Filas locais e de rede
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Dados coletados pelo agente sem alterar configurações da máquina.
          </p>
        </div>

        <div className="mt-6 table-shell">
          {printers.length === 0 ? (
            <div className="px-4 py-10 text-center text-slate-500">Nenhuma impressora detectada pelo agente.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Driver</th>
                  <th>Porta</th>
                  <th>Servidor</th>
                  <th>Compartilhamento</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {printers.map((printer) => (
                  <tr key={printer.id}>
                    <td>
                      <div className="flex flex-col gap-1">
                        <span className="font-semibold text-slate-900">{printer.name}</span>
                        <div className="flex flex-wrap gap-2">
                          {printer.is_default && <span className="status-online">Padrao</span>}
                          {printer.is_network && <span className="status-neutral">Rede</span>}
                          {printer.is_shared && <span className="status-warning">Compartilhada</span>}
                        </div>
                      </div>
                    </td>
                    <td>{printer.driver_name || "-"}</td>
                    <td>{printer.port_name || "-"}</td>
                    <td>{printer.server_name || "-"}</td>
                    <td>{printer.share_name || "-"}</td>
                    <td>{printer.status || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Relação de ativos
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
