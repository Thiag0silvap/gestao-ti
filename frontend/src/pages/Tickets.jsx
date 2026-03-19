import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

const initialForm = {
  title: "",
  description: "",
  priority: "Média",
  status: "Aberto",
  assigned_to_id: "",
  computer_id: "",
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

  const handleAuthError = (error, defaultMessage) => {
    console.error(error);

    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      navigate("/");
      return;
    }

    alert(defaultMessage);
  };

  const loadTickets = () => {
    api.get("/tickets")
      .then((response) => setTickets(response.data))
      .catch((error) => handleAuthError(error, "Erro ao carregar chamados"));
  };

  const loadComputers = () => {
    api.get("/computers")
      .then((response) => setComputers(response.data))
      .catch(() => {});
  };

  const loadUsers = () => {
    api.get("/users")
      .then((response) => setUsers(response.data))
      .catch(() => {});
  };

  useEffect(() => {
    loadTickets();
    loadComputers();

    if (currentUser?.role === "admin") {
      loadUsers();
    }
  }, []);

  const filteredTickets = useMemo(() => {
    return tickets.filter((ticket) => {
      const searchText = search.toLowerCase();

      const matchesSearch =
        ticket.title?.toLowerCase().includes(searchText) ||
        ticket.description?.toLowerCase().includes(searchText);

      const matchesStatus = !statusFilter || ticket.status === statusFilter;
      const matchesPriority = !priorityFilter || ticket.priority === priorityFilter;

      return matchesSearch && matchesStatus && matchesPriority;
    });
  }, [tickets, search, statusFilter, priorityFilter]);

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: value,
    }));
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
        await api.put(`/tickets/${editingId}`, payload);
        alert("Chamado atualizado com sucesso!");
      } else {
        await api.post("/tickets", {
          title: payload.title,
          description: payload.description,
          priority: payload.priority,
          assigned_to_id: payload.assigned_to_id,
          computer_id: payload.computer_id,
        });
        alert("Chamado criado com sucesso!");
      }

      resetForm();
      loadTickets();
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.detail || "Erro ao salvar chamado");
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
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (ticketId) => {
    const confirmed = window.confirm("Deseja realmente excluir este chamado?");
    if (!confirmed) return;

    try {
      await api.delete(`/tickets/${ticketId}`);
      alert("Chamado excluído com sucesso!");
      loadTickets();

      if (editingId === ticketId) {
        resetForm();
      }
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.detail || "Erro ao excluir chamado");
    }
  };

  const getStatusClass = (status) => {
    if (status === "Aberto") return "bg-blue-100 text-blue-700";
    if (status === "Em atendimento") return "bg-yellow-100 text-yellow-700";
    if (status === "Resolvido") return "bg-green-100 text-green-700";
    if (status === "Fechado") return "bg-slate-200 text-slate-700";
    return "bg-slate-200 text-slate-700";
  };

  const getPriorityClass = (priority) => {
    if (priority === "Baixa") return "bg-slate-200 text-slate-700";
    if (priority === "Média") return "bg-blue-100 text-blue-700";
    if (priority === "Alta") return "bg-orange-100 text-orange-700";
    if (priority === "Crítica") return "bg-red-100 text-red-700";
    return "bg-slate-200 text-slate-700";
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-slate-800">Chamados</h2>
        <p className="text-slate-500">Gerenciamento de chamados do sistema</p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-xl font-bold text-slate-800">
          {editingId ? "Editar chamado" : "Abrir chamado"}
        </h3>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <input
            type="text"
            name="title"
            placeholder="Título"
            value={form.title}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            required
          />

          <select
            name="priority"
            value={form.priority}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          >
            <option value="Baixa">Baixa</option>
            <option value="Média">Média</option>
            <option value="Alta">Alta</option>
            <option value="Crítica">Crítica</option>
          </select>

          <select
            name="computer_id"
            value={form.computer_id}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          >
            <option value="">Nenhum computador</option>
            {computers.map((computer) => (
              <option key={computer.id} value={computer.id}>
                {computer.hostname}
              </option>
            ))}
          </select>

          {editingId && currentUser?.role !== "operator" && (
            <>
              <select
                name="status"
                value={form.status}
                onChange={handleChange}
                className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
              >
                <option value="Aberto">Aberto</option>
                <option value="Em atendimento">Em atendimento</option>
                <option value="Resolvido">Resolvido</option>
                <option value="Fechado">Fechado</option>
              </select>

              {currentUser?.role === "admin" && (
                <select
                  name="assigned_to_id"
                  value={form.assigned_to_id}
                  onChange={handleChange}
                  className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
                >
                  <option value="">Nenhum responsável</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name}
                    </option>
                  ))}
                </select>
              )}
            </>
          )}

          <textarea
            name="description"
            placeholder="Descrição do problema"
            value={form.description}
            onChange={handleChange}
            rows="4"
            className="md:col-span-2 xl:col-span-3 rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            required
          />

          <div className="md:col-span-2 xl:col-span-3 flex gap-3">
            <button
              type="submit"
              className="rounded-lg bg-slate-900 px-4 py-3 text-white hover:bg-slate-800"
            >
              {editingId ? "Salvar alterações" : "Abrir chamado"}
            </button>

            {editingId && (
              <button
                type="button"
                onClick={resetForm}
                className="rounded-lg bg-slate-200 px-4 py-3 text-slate-800 hover:bg-slate-300"
              >
                Cancelar edição
              </button>
            )}
          </div>
        </form>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <input
            type="text"
            placeholder="Buscar por título ou descrição"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          />

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          >
            <option value="">Todos os status</option>
            <option value="Aberto">Aberto</option>
            <option value="Em atendimento">Em atendimento</option>
            <option value="Resolvido">Resolvido</option>
            <option value="Fechado">Fechado</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          >
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
            className="rounded-lg bg-slate-200 px-4 py-3 text-slate-800 hover:bg-slate-300"
          >
            Limpar filtros
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
        <table className="min-w-full">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-4 py-3 text-left">Título</th>
              <th className="px-4 py-3 text-left">Setor</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Prioridade</th>
              <th className="px-4 py-3 text-left">Solicitante</th>
              <th className="px-4 py-3 text-left">Responsável</th>
              <th className="px-4 py-3 text-left">Ações</th>
            </tr>
          </thead>
          <tbody>
            {filteredTickets.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-6 text-center text-slate-500">
                  Nenhum chamado encontrado.
                </td>
              </tr>
            ) : (
              filteredTickets.map((ticket) => (
                <tr key={ticket.id} className="border-t border-slate-200">
                  <td className="px-4 py-3">{ticket.title}</td>
                  <td className="px-4 py-3">{ticket.sector || "-"}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-3 py-1 text-sm font-medium ${getStatusClass(ticket.status)}`}>
                      {ticket.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-3 py-1 text-sm font-medium ${getPriorityClass(ticket.priority)}`}>
                      {ticket.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">{ticket.requester_id}</td>
                  <td className="px-4 py-3">{ticket.assigned_to_id || "-"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(ticket)}
                        className="rounded-lg bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600"
                      >
                        Editar
                      </button>

                      {currentUser?.role === "admin" && (
                        <button
                          onClick={() => handleDelete(ticket.id)}
                          className="rounded-lg bg-red-500 px-3 py-2 text-sm text-white hover:bg-red-600"
                        >
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
      </div>
    </div>
  );
}

export default Tickets;