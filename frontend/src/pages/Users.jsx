import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/api";
import TableControls from "../components/TableControls";
import { useUI } from "../components/UIContext";
import useAutoRefresh from "../hooks/useAutoRefresh";
import useDataTable from "../hooks/useDataTable";
import { getStoredUser } from "../services/sessionService";

const initialForm = {
  name: "",
  username: "",
  password: "",
  role: "operator",
  sector: "",
  is_active: true,
};

function Users() {
  const [users, setUsers] = useState([]);
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();
  const currentUser = getStoredUser();
  const { notify, confirm } = useUI();

  const upsertUser = useCallback((userData) => {
    setUsers((current) => {
      const exists = current.some((item) => item.id === userData.id);
      if (exists) {
        return current.map((item) => (item.id === userData.id ? userData : item));
      }
      return [userData, ...current];
    });
  }, []);

  const loadUsers = useCallback(async () => {
    try {
      const response = await api.get("/users");
      setUsers(response.data);
      return response.data;
    } catch (error) {
      console.error(error);

      if (error.response?.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        navigate("/");
      } else if (error.response?.status === 403) {
        notify("Você não tem permissão para acessar usuários.", "error");
        navigate("/dashboard");
      } else {
        notify("Erro ao carregar usuários", "error");
      }

      return [];
    }
  }, [navigate, notify]);

  useAutoRefresh(loadUsers);

  const roles = useMemo(() => [...new Set(users.map((user) => user.role).filter(Boolean))], [users]);

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const searchText = search.toLowerCase();
      const matchesSearch =
        user.name?.toLowerCase().includes(searchText) ||
        user.username?.toLowerCase().includes(searchText) ||
        user.sector?.toLowerCase().includes(searchText);

      const matchesRole = !roleFilter || user.role === roleFilter;
      return matchesSearch && matchesRole;
    });
  }, [users, search, roleFilter]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;

    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const resetForm = () => {
    setForm(initialForm);
    setEditingId(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const payload = {
        ...form,
        password: form.password || null,
      };

      let savedUser;

      if (editingId) {
        const response = await api.put(`/users/${editingId}`, payload);
        savedUser = response.data;
        upsertUser(savedUser);
        notify("Usuário atualizado com sucesso!", "success");
      } else {
        const response = await api.post("/users", payload);
        savedUser = response.data;
        upsertUser(savedUser);
        notify("Usuário cadastrado com sucesso!", "success");
      }

      setSearch(savedUser?.username || "");
      setRoleFilter(savedUser?.role || "");
      setPage(1);
      resetForm();
    } catch (error) {
      console.error(error);

      if (error.response?.data?.detail) {
        notify(error.response.data.detail, "error");
      } else {
        notify("Erro ao salvar usuário", "error");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEdit = (user) => {
    setEditingId(user.id);
    setForm({
      name: user.name ?? "",
      username: user.username ?? "",
      password: "",
      role: user.role ?? "operator",
      sector: user.sector ?? "",
      is_active: user.is_active ?? true,
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleToggleStatus = async (userId) => {
    try {
      const response = await api.patch(`/users/${userId}/status`);
      upsertUser(response.data);
      notify("Status do usuário atualizado!", "success");
    } catch (error) {
      console.error(error);
      notify(error.response?.data?.detail || "Erro ao alterar status do usuário", "error");
    }
  };

  const handleDelete = async (userId) => {
    const confirmed = await confirm({
      title: "Excluir usuário",
      message: "Deseja realmente excluir este usuário? Esta ação não pode ser desfeita.",
      confirmLabel: "Excluir",
      cancelLabel: "Cancelar",
      tone: "danger",
    });

    if (!confirmed) return;

    try {
      await api.delete(`/users/${userId}`);
      setUsers((current) => current.filter((user) => user.id !== userId));
      notify("Usuário excluído com sucesso!", "success");

      if (editingId === userId) {
        resetForm();
      }
    } catch (error) {
      console.error(error);
      notify(error.response?.data?.detail || "Erro ao excluir usuário", "error");
    }
  };

  const activeUsers = filteredUsers.filter((user) => user.is_active).length;

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
  } = useDataTable(filteredUsers, {
    initialSort: { key: "name", direction: "asc" },
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
            Acessos e perfis
          </p>
          <h2 className="page-title mt-3 text-3xl md:text-[2.6rem]">
            Controle quem entra, com qual perfil e em qual contexto operacional.
          </h2>
          <p className="page-subtitle">
            Administre usuários ativos, níveis de acesso e setores sem perder clareza na gestão.
          </p>
        </div>

        <div className="section-card">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Total</p>
              <p className="mt-3 text-3xl font-semibold text-slate-900">{filteredUsers.length}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Ativos</p>
              <p className="mt-3 text-3xl font-semibold text-emerald-700">{activeUsers}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Perfis</p>
              <p className="mt-3 text-3xl font-semibold text-amber-700">{roles.length}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Cadastro</p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              {editingId ? "Editar usuário" : "Cadastrar usuário"}
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Somente administradores podem criar, editar ou desativar acessos.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
          <input type="text" name="name" placeholder="Nome completo" value={form.name} onChange={handleChange} className="field-input" required />
          <input type="text" name="username" placeholder="Usuário" value={form.username} onChange={handleChange} className="field-input" required />
          <input
            type="password"
            name="password"
            placeholder={editingId ? "Nova senha (opcional)" : "Senha"}
            value={form.password}
            onChange={handleChange}
            className="field-input"
            required={!editingId}
          />
          <select name="role" value={form.role} onChange={handleChange} className="field-input">
            <option value="admin">admin</option>
            <option value="technician">technician</option>
            <option value="operator">operator</option>
          </select>
          <input type="text" name="sector" placeholder="Setor" value={form.sector} onChange={handleChange} className="field-input" />

          <label className="flex items-center gap-3 rounded-[20px] border border-slate-200 bg-white/70 px-4 py-3 text-slate-700">
            <input type="checkbox" name="is_active" checked={form.is_active} onChange={handleChange} />
            Usuário ativo
          </label>

          <div className="flex flex-wrap gap-3 md:col-span-2">
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting
                ? (editingId ? "Salvando..." : "Cadastrando...")
                : (editingId ? "Salvar alterações" : "Cadastrar usuário")}
            </button>

            {editingId && (
              <button type="button" onClick={resetForm} className="btn-secondary">
                Cancelar edição
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="section-card">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <input type="text" placeholder="Buscar por nome, usuário ou setor" value={search} onChange={(e) => setSearch(e.target.value)} className="field-input" />

          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="field-input">
            <option value="">Todos os perfis</option>
            {roles.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              setSearch("");
              setRoleFilter("");
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
              <th><button type="button" onClick={() => requestSort("name")} className="table-sort-button">Nome <span className="table-sort-indicator">{getSortIndicator("name")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("username")} className="table-sort-button">Usuário <span className="table-sort-indicator">{getSortIndicator("username")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("role")} className="table-sort-button">Perfil <span className="table-sort-indicator">{getSortIndicator("role")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("sector")} className="table-sort-button">Setor <span className="table-sort-indicator">{getSortIndicator("sector")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("is_active")} className="table-sort-button">Status <span className="table-sort-indicator">{getSortIndicator("is_active")}</span></button></th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {totalItems === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-10 text-center text-slate-500">
                  Nenhum usuário encontrado.
                </td>
              </tr>
            ) : (
              paginatedItems.map((user) => (
                <tr key={user.id}>
                  <td>{user.name}</td>
                  <td>{user.username}</td>
                  <td>{user.role}</td>
                  <td>{user.sector || "-"}</td>
                  <td>
                    <span className={user.is_active ? "status-online" : "status-offline"}>
                      {user.is_active ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => handleEdit(user)} className="btn-secondary px-3 py-2 text-sm">
                        Editar
                      </button>

                      <button onClick={() => handleToggleStatus(user.id)} className="btn-secondary px-3 py-2 text-sm">
                        {user.is_active ? "Desativar" : "Ativar"}
                      </button>

                      {currentUser?.id !== user.id && (
                        <button onClick={() => handleDelete(user.id)} className="btn-danger px-3 py-2 text-sm">
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
          itemLabel="usuários"
        />
      </section>
    </div>
  );
}

export default Users;
