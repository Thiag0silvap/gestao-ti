import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

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

  const navigate = useNavigate();
  const currentUser = JSON.parse(localStorage.getItem("user"));

  const loadUsers = () => {
    api.get("/users")
      .then((response) => setUsers(response.data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          navigate("/");
        } else if (error.response?.status === 403) {
          alert("Você não tem permissão para acessar usuários.");
          navigate("/dashboard");
        } else {
          alert("Erro ao carregar usuários");
        }
      });
  };

  useEffect(() => {
    loadUsers();
  }, []);

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

    try {
      const payload = {
        ...form,
        password: form.password || null,
      };

      if (editingId) {
        await api.put(`/users/${editingId}`, payload);
        alert("Usuário atualizado com sucesso!");
      } else {
        await api.post("/users", payload);
        alert("Usuário cadastrado com sucesso!");
      }

      resetForm();
      loadUsers();
    } catch (error) {
      console.error(error);

      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert("Erro ao salvar usuário");
      }
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
      await api.patch(`/users/${userId}/status`);
      alert("Status do usuário atualizado!");
      loadUsers();
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.detail || "Erro ao alterar status do usuário");
    }
  };

  const handleDelete = async (userId) => {
    const confirmed = window.confirm("Deseja realmente excluir este usuário?");

    if (!confirmed) return;

    try {
      await api.delete(`/users/${userId}`);
      alert("Usuário excluído com sucesso!");
      loadUsers();

      if (editingId === userId) {
        resetForm();
      }
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.detail || "Erro ao excluir usuário");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-slate-800">Usuários</h2>
        <p className="text-slate-500">Gerenciamento de usuários do sistema</p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-xl font-bold text-slate-800">
          {editingId ? "Editar usuário" : "Cadastrar usuário"}
        </h3>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <input
            type="text"
            name="name"
            placeholder="Nome completo"
            value={form.name}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            required
          />

          <input
            type="text"
            name="username"
            placeholder="Usuário"
            value={form.username}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            required
          />

          <input
            type="password"
            name="password"
            placeholder={editingId ? "Nova senha (opcional)" : "Senha"}
            value={form.password}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            required={!editingId}
          />

          <select
            name="role"
            value={form.role}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          >
            <option value="admin">admin</option>
            <option value="technician">technician</option>
            <option value="operator">operator</option>
          </select>

          <input
            type="text"
            name="sector"
            placeholder="Setor"
            value={form.sector}
            onChange={handleChange}
            className="rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
          />

          <label className="flex items-center gap-2 text-slate-700">
            <input
              type="checkbox"
              name="is_active"
              checked={form.is_active}
              onChange={handleChange}
            />
            Usuário ativo
          </label>

          <div className="md:col-span-2 flex gap-3">
            <button
              type="submit"
              className="rounded-lg bg-slate-900 px-4 py-3 text-white hover:bg-slate-800"
            >
              {editingId ? "Salvar alterações" : "Cadastrar usuário"}
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

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
        <table className="min-w-full">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-4 py-3 text-left">Nome</th>
              <th className="px-4 py-3 text-left">Usuário</th>
              <th className="px-4 py-3 text-left">Perfil</th>
              <th className="px-4 py-3 text-left">Setor</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Ações</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-4 py-6 text-center text-slate-500">
                  Nenhum usuário encontrado.
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="border-t border-slate-200">
                  <td className="px-4 py-3">{user.name}</td>
                  <td className="px-4 py-3">{user.username}</td>
                  <td className="px-4 py-3">{user.role}</td>
                  <td className="px-4 py-3">{user.sector || "-"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-3 py-1 text-sm font-medium ${
                        user.is_active
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {user.is_active ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(user)}
                        className="rounded-lg bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600"
                      >
                        Editar
                      </button>

                      <button
                        onClick={() => handleToggleStatus(user.id)}
                        className="rounded-lg bg-yellow-500 px-3 py-2 text-sm text-white hover:bg-yellow-600"
                      >
                        {user.is_active ? "Desativar" : "Ativar"}
                      </button>

                      {currentUser?.id !== user.id && (
                        <button
                          onClick={() => handleDelete(user.id)}
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

export default Users;