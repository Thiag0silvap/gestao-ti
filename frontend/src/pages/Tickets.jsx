import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/api";
import TableControls from "../components/TableControls";
import { useUI } from "../components/UIProvider";
import useAutoRefresh from "../hooks/useAutoRefresh";
import useDataTable from "../hooks/useDataTable";

const initialForm = {
  title: "",
  description: "",
  priority: "Média",
  status: "Aberto",
  assigned_to_id: "",
  computer_id: "",
  sector: "",
};

function Tickets() {
  const [tickets, setTickets] = useState([]);
  const [computers, setComputers] = useState([]);
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");

  const navigate = useNavigate();
  const currentUser = JSON.parse(localStorage.getItem("user"));
  const { notify, confirm } = useUI();

  const upsertTicket = useCallback((ticketData) => {
    setTickets((current) => {
      const exists = current.some((item) => item.id === ticketData.id);
      if (exists) {
        return current.map((item) => (item.id === ticketData.id ? ticketData : item));
      }
      return [ticketData, ...current];
    });
  }, []);

  const handleAuthError = (error, defaultMessage) => {
    console.error(error);

    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      navigate("/");
      return;
    }

    notify(defaultMessage, "error");
  };

  const loadTickets = useCallback(() => {
    api
      .get("/tickets")
      .then((response) => setTickets(response.data))
      .catch((error) => handleAuthError(error, "Erro ao carregar chamados"));
  }, [navigate, notify]);

  const loadComputers = useCallback(() => {
    api
      .get("/computers")
      .then((response) => setComputers(response.data))
      .catch(() => {});
  }, []);

  const loadUsers = useCallback(() => {
    api
      .get("/users")
      .then((response) => setUsers(response.data))
      .catch(() => {});
  }, []);

  const refreshPage = useCallback(() => {
    loadTickets();
    loadComputers();

    if (currentUser?.role === "admin") {
      loadUsers();
    }
  }, [currentUser?.role, loadComputers, loadTickets, loadUsers]);

  useAutoRefresh(refreshPage);

  const filteredTickets = useMemo(() => {
    return tickets.filter((ticket) => {
      const searchText = search.toLowerCase();

      const matchesSearch =
        ticket.title?.toLowerCase().includes(searchText) ||
        ticket.description?.toLowerCase().includes(searchText) ||
        ticket.requester_name?.toLowerCase().includes(searchText) ||
        ticket.computer_hostname?.toLowerCase().includes(searchText);

      const matchesStatus = !statusFilter || ticket.status === statusFilter;
      const matchesPriority = !priorityFilter || ticket.priority === priorityFilter;

      return matchesSearch && matchesStatus && matchesPriority;
    });
  }, [tickets, search, statusFilter, priorityFilter]);

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => {
      const next = {
        ...prev,
        [name]: value,
      };

      if (name === "computer_id") {
        const selectedComputer = computers.find((computer) => computer.id === Number(value));
        if (selectedComputer) {
          next.sector = selectedComputer.sector || prev.sector;
        }
      }

      return next;
    });
  };

  const resetForm = () => {
    setForm(initialForm);
    setEditingId(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const payload = {
      ...form,
      assigned_to_id: form.assigned_to_id ? Number(form.assigned_to_id) : null,
      computer_id: form.computer_id ? Number(form.computer_id) : null,
    };

    try {
      if (editingId) {
        const response = await api.put(`/tickets/${editingId}`, payload);
        upsertTicket(response.data);
        notify("Chamado atualizado com sucesso!", "success");
      } else {
        const response = await api.post("/tickets", {
          title: payload.title,
          description: payload.description,
          priority: payload.priority,
          assigned_to_id: payload.assigned_to_id,
          computer_id: payload.computer_id,
        });
        upsertTicket(response.data);
        notify("Chamado criado com sucesso!", "success");
      }

      resetForm();
    } catch (error) {
      console.error(error);
      notify(error.response?.data?.detail || "Erro ao salvar chamado", "error");
    }
  };

  const handleEdit = (ticket) => {
    setEditingId(ticket.id);
    setForm({
      title: ticket.title ?? "",
      description: ticket.description ?? "",
      priority: ticket.priority ?? "Média",
      status: ticket.status ?? "Aberto",
      assigned_to_id: ticket.assigned_to_id ?? "",
      computer_id: ticket.computer_id ?? "",
      sector: ticket.sector ?? "",
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (ticketId) => {
    const confirmed = await confirm({
      title: "Excluir chamado",
      message: "Deseja realmente excluir este chamado? Esta acao nao pode ser desfeita.",
      confirmLabel: "Excluir",
      cancelLabel: "Cancelar",
      tone: "danger",
    });
    if (!confirmed) return;

    try {
      await api.delete(`/tickets/${ticketId}`);
      setTickets((current) => current.filter((ticket) => ticket.id !== ticketId));
      notify("Chamado excluido com sucesso!", "success");

      if (editingId === ticketId) {
        resetForm();
      }
    } catch (error) {
      console.error(error);
      notify(error.response?.data?.detail || "Erro ao excluir chamado", "error");
    }
  };

  const getStatusClass = (status) => {
    if (status === "Resolvido") return "status-online";
    if (status === "Fechado") return "status-neutral";
    if (status === "Em atendimento") return "status-neutral";
    return "status-offline";
  };

  const getPriorityClass = (priority) => {
    if (priority === "Crítica") return "status-offline";
    if (priority === "Alta") return "status-neutral";
    if (priority === "Média") return "status-online";
    return "status-neutral";
  };

  const openTickets = filteredTickets.filter((ticket) => ticket.status !== "Fechado" && ticket.status !== "Resolvido").length;

  const {
    sortConfig,
    requestSort,
    page,
    setPage,
    pageSize,
    setPageSize,
    totalPages,
    totalItems,
    paginatedItems,
  } = useDataTable(filteredTickets, {
    initialSort: { key: "title", direction: "asc" },
  });

  const getSortIndicator = (key) => {
    if (sortConfig?.key !== key) return "↕";
    return sortConfig.direction === "asc" ? "↑" : "↓";
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="section-card">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Fluxo de suporte
          </p>
          <h2 className="page-title mt-3 text-3xl md:text-[2.6rem]">
            Registre, acompanhe e distribua chamados com mais contexto tecnico.
          </h2>
          <p className="page-subtitle">
            Conecte o atendimento ao equipamento, setor e responsavel para acelerar o suporte.
          </p>
        </div>

        <div className="section-card">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Total</p>
              <p className="mt-3 text-3xl font-semibold text-slate-900">{filteredTickets.length}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Em aberto</p>
              <p className="mt-3 text-3xl font-semibold text-rose-700">{openTickets}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Resolvidos</p>
              <p className="mt-3 text-3xl font-semibold text-emerald-700">
                {filteredTickets.filter((ticket) => ticket.status === "Resolvido" || ticket.status === "Fechado").length}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Formulario</p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              {editingId ? "Atualizar chamado" : "Abrir chamado"}
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            O setor pode ser preenchido automaticamente ao selecionar um computador.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div>
            <label className="field-label">Titulo</label>
            <input type="text" name="title" value={form.title} onChange={handleChange} className="field-input" required />
          </div>

          <div>
            <label className="field-label">Prioridade</label>
            <select name="priority" value={form.priority} onChange={handleChange} className="field-input">
              <option value="Baixa">Baixa</option>
              <option value="Média">Média</option>
              <option value="Alta">Alta</option>
              <option value="Crítica">Crítica</option>
            </select>
          </div>

          <div>
            <label className="field-label">Computador</label>
            <select name="computer_id" value={form.computer_id} onChange={handleChange} className="field-input">
              <option value="">Identificar automaticamente</option>
              {computers.map((computer) => (
                <option key={computer.id} value={computer.id}>
                  {computer.hostname}
                </option>
              ))}
            </select>
          </div>

          {editingId && currentUser?.role !== "operator" && (
            <>
              <div>
                <label className="field-label">Status</label>
                <select name="status" value={form.status} onChange={handleChange} className="field-input">
                  <option value="Aberto">Aberto</option>
                  <option value="Em atendimento">Em atendimento</option>
                  <option value="Resolvido">Resolvido</option>
                  <option value="Fechado">Fechado</option>
                </select>
              </div>

              {currentUser?.role === "admin" && (
                <div>
                  <label className="field-label">Responsavel</label>
                  <select name="assigned_to_id" value={form.assigned_to_id} onChange={handleChange} className="field-input">
                    <option value="">Nenhum responsavel</option>
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div>
                <label className="field-label">Setor</label>
                <input type="text" name="sector" value={form.sector} onChange={handleChange} className="field-input" />
              </div>
            </>
          )}

          <div className="md:col-span-2 xl:col-span-3">
            <label className="field-label">Descricao</label>
            <textarea name="description" value={form.description} onChange={handleChange} rows="4" className="field-input" required />
          </div>

          <div className="flex flex-wrap gap-3 md:col-span-2 xl:col-span-3">
            <button type="submit" className="btn-primary">
              {editingId ? "Salvar alteracoes" : "Abrir chamado"}
            </button>

            {editingId && (
              <button type="button" onClick={resetForm} className="btn-secondary">
                Cancelar edicao
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="section-card">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <input type="text" placeholder="Titulo, descricao, solicitante ou computador" value={search} onChange={(e) => setSearch(e.target.value)} className="field-input" />

          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="field-input">
            <option value="">Todos os status</option>
            <option value="Aberto">Aberto</option>
            <option value="Em atendimento">Em atendimento</option>
            <option value="Resolvido">Resolvido</option>
            <option value="Fechado">Fechado</option>
          </select>

          <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)} className="field-input">
            <option value="">Todas as prioridades</option>
            <option value="Baixa">Baixa</option>
            <option value="Média">Média</option>
            <option value="Alta">Alta</option>
            <option value="Crítica">Crítica</option>
          </select>

          <button
            onClick={() => {
              setSearch("");
              setStatusFilter("");
              setPriorityFilter("");
            }}
            className="btn-secondary"
          >
            Limpar filtros
          </button>
        </div>
      </section>

      <section className="table-shell">
        <table>
          <thead>
            <tr>
              <th><button type="button" onClick={() => requestSort("title")} className="table-sort-button">Titulo <span className="table-sort-indicator">{getSortIndicator("title")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("sector")} className="table-sort-button">Setor <span className="table-sort-indicator">{getSortIndicator("sector")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("computer_hostname")} className="table-sort-button">Computador <span className="table-sort-indicator">{getSortIndicator("computer_hostname")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("status")} className="table-sort-button">Status <span className="table-sort-indicator">{getSortIndicator("status")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("priority")} className="table-sort-button">Prioridade <span className="table-sort-indicator">{getSortIndicator("priority")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("requester_name")} className="table-sort-button">Solicitante <span className="table-sort-indicator">{getSortIndicator("requester_name")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("assigned_to_name")} className="table-sort-button">Responsavel <span className="table-sort-indicator">{getSortIndicator("assigned_to_name")}</span></button></th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {totalItems === 0 ? (
              <tr>
                <td colSpan="8" className="px-4 py-10 text-center text-slate-500">
                  Nenhum chamado encontrado.
                </td>
              </tr>
            ) : (
              paginatedItems.map((ticket) => (
                <tr key={ticket.id}>
                  <td>{ticket.title}</td>
                  <td>{ticket.sector || "-"}</td>
                  <td>{ticket.computer_hostname || "-"}</td>
                  <td>
                    <span className={getStatusClass(ticket.status)}>{ticket.status}</span>
                  </td>
                  <td>
                    <span className={getPriorityClass(ticket.priority)}>{ticket.priority}</span>
                  </td>
                  <td>{ticket.requester_name || "-"}</td>
                  <td>{ticket.assigned_to_name || "-"}</td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => handleEdit(ticket)} className="btn-secondary px-3 py-2 text-sm">
                        Editar
                      </button>

                      {currentUser?.role === "admin" && (
                        <button onClick={() => handleDelete(ticket.id)} className="btn-danger px-3 py-2 text-sm">
                          Excluir
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        <TableControls
          page={page}
          totalPages={totalPages}
          pageSize={pageSize}
          setPage={setPage}
          setPageSize={setPageSize}
          totalItems={totalItems}
          itemLabel="chamados"
        />
      </section>
    </div>
  );
}

export default Tickets;
