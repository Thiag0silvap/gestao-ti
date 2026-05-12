import React, { useState, useEffect } from "react";
import { getAuditLogs } from "../services/auditService";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";

const AuditLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    action: "",
    username: "",
    limit: 50,
    offset: 0
  });

  const [selectedLog, setSelectedLog] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await getAuditLogs(filters);
      setLogs(data);
      setError(null);
    } catch (err) {
      setError("Falha ao carregar logs de auditoria.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [filters]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value, offset: 0 }));
  };

  const handlePageChange = (direction) => {
    const newOffset = direction === 'next' 
      ? filters.offset + filters.limit 
      : Math.max(0, filters.offset - filters.limit);
    setFilters(prev => ({ ...prev, offset: newOffset }));
  };

  const openDetails = (log) => {
    setSelectedLog(log);
    setIsModalOpen(true);
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case "SUCCESS": return "status-online";
      case "FAILURE": return "status-critical";
      case "WARNING": return "status-warning";
      default: return "status-neutral";
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Logs do Sistema</h1>
        <p className="page-subtitle">Rastreabilidade completa de ações administrativas e eventos operacionais.</p>
      </div>

      {/* Filters Bar */}
      <div className="section-card grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="flex flex-col">
          <label className="field-label">Usuário</label>
          <input
            type="text"
            name="username"
            placeholder="Ex: thiago"
            value={filters.username}
            onChange={handleFilterChange}
            className="field-input"
          />
        </div>
        <div className="flex flex-col">
          <label className="field-label">Ação</label>
          <select
            name="action"
            value={filters.action}
            onChange={handleFilterChange}
            className="field-input"
          >
            <option value="">Todas as ações</option>
            <option value="LOGIN_SUCCESS">Login Sucesso</option>
            <option value="LOGIN_FAILURE">Login Falha</option>
            <option value="LOGIN_BLOCKED">Login Bloqueado (Segurança)</option>
            <option value="REMOTE_COMMAND_SENT">Comando Remoto Enviado</option>
            <option value="REMOTE_COMMAND_CANCELLED">Comando Remoto Cancelado</option>
            <option value="COMPUTER_UPDATED">Computador Atualizado</option>
            <option value="COMPUTER_DELETED">Computador Deletado</option>
            <option value="TICKET_CREATED">Chamado Criado</option>
            <option value="TICKET_UPDATED">Chamado Atualizado</option>
            <option value="TICKET_DELETED">Chamado Deletado</option>
            <option value="USER_CREATED">Usuário Criado</option>
            <option value="USER_UPDATED">Usuário Editado</option>
            <option value="USER_DELETED">Usuário Deletado</option>
            <option value="USER_STATUS_TOGGLED">Status de Usuário Alterado</option>
            <option value="ASSET_CREATED">Ativo Criado</option>
            <option value="ASSET_UPDATED">Ativo Atualizado</option>
            <option value="ASSET_DELETED">Ativo Deletado</option>
            <option value="SYSTEM_STARTUP">Inicialização do Sistema</option>

          </select>
        </div>
        <div className="md:col-span-2 flex items-end justify-end gap-3">
          <button 
            onClick={() => setFilters({ action: "", username: "", limit: 50, offset: 0 })}
            className="btn-secondary"
          >
            Limpar Filtros
          </button>
          <button 
            onClick={fetchLogs}
            className="btn-primary"
          >
            Atualizar
          </button>
        </div>
      </div>

      {/* Logs Table */}
      <div className="table-shell">
        <table className="w-full">
          <thead>
            <tr>
              <th>Data/Hora</th>
              <th>Usuário</th>
              <th>Ação</th>
              <th>Entidade</th>
              <th>Status</th>
              <th>Origem</th>
              <th className="text-right">Detalhes</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="7" className="py-20 text-center">
                  <div className="flex flex-col items-center gap-3">
                    <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500/20 border-t-emerald-500" />
                    <p className="text-sm font-medium text-slate-500">Carregando auditoria...</p>
                  </div>
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan="7" className="py-20 text-center text-slate-400 italic">
                  Nenhum log encontrado.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id}>
                  <td className="font-mono text-xs">
                    {format(new Date(log.created_at), "dd/MM/yy HH:mm:ss", { locale: ptBR })}
                  </td>
                  <td>
                    <div className="flex flex-col">
                      <span className="font-semibold text-slate-900">{log.username}</span>
                      <span className="text-[10px] text-slate-400">ID: {log.user_id || "-"}</span>
                    </div>
                  </td>
                  <td>
                    <span className="text-[11px] font-bold text-emerald-800 bg-emerald-100/50 px-2 py-0.5 rounded">
                      {log.action}
                    </span>
                  </td>
                  <td>
                    <div className="flex flex-col">
                      <span className="text-xs text-slate-600">{log.entity_type || "-"}</span>
                      <span className="text-[10px] text-slate-400">ID: {log.entity_id || "-"}</span>
                    </div>
                  </td>
                  <td>
                    <span className={getStatusBadgeClass(log.status)}>
                      {log.status}
                    </span>
                  </td>
                  <td className="font-mono text-xs text-slate-500">
                    {log.ip_address || "127.0.0.1"}
                  </td>
                  <td className="text-right">
                    <button 
                      onClick={() => openDetails(log)}
                      className="text-emerald-700 hover:text-emerald-900 font-bold px-3 py-1 bg-emerald-50 hover:bg-emerald-100 rounded-lg transition-colors"
                    >
                      [+]
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        <div className="flex items-center justify-between bg-slate-50/50 px-6 py-4 border-t border-slate-100">
          <p className="text-xs text-slate-500 font-semibold tracking-wider uppercase">
            Página {Math.floor(filters.offset / filters.limit) + 1}
          </p>
          <div className="flex gap-2">
            <button 
              disabled={filters.offset === 0}
              onClick={() => handlePageChange('prev')}
              className="btn-secondary py-1.5 px-3 text-xs"
            >
              Anterior
            </button>
            <button 
              disabled={logs.length < filters.limit}
              onClick={() => handlePageChange('next')}
              className="btn-secondary py-1.5 px-3 text-xs"
            >
              Próxima
            </button>
          </div>
        </div>
      </div>

      {/* Details Modal */}
      {isModalOpen && selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onClick={() => setIsModalOpen(false)} />
          <div className="relative w-full max-w-2xl overflow-hidden rounded-[var(--radius-xl)] bg-white shadow-2xl animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between border-b border-slate-100 px-8 py-6 bg-slate-50/50">
              <h3 className="text-xl font-bold text-slate-900">Inspeção de Log</h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-2xl"
              >
                &times;
              </button>
            </div>
            <div className="p-8 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-6 mb-8">
                <div>
                  <p className="field-label">Ação</p>
                  <p className="text-slate-900 font-semibold">{selectedLog.action}</p>
                </div>
                <div>
                  <p className="field-label">Data Completa</p>
                  <p className="text-slate-900 font-semibold">{format(new Date(selectedLog.created_at), "PPPPp", { locale: ptBR })}</p>
                </div>
                <div className="col-span-2">
                  <p className="field-label">Agente do Navegador</p>
                  <p className="text-slate-600 text-xs font-mono bg-slate-50 p-3 rounded-xl border border-slate-100 break-all">
                    {selectedLog.user_agent || "Desconhecido"}
                  </p>
                </div>
              </div>
              
              <p className="field-label">Metadados da Operação (JSON)</p>
              <pre className="rounded-2xl border border-emerald-100 bg-[#15231f] p-5 text-sm text-emerald-400 font-mono overflow-x-auto shadow-inner">
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </div>
            <div className="flex justify-end bg-slate-50 p-6 border-t border-slate-100">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="btn-primary"
              >
                Fechar Inspeção
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AuditLogs;
