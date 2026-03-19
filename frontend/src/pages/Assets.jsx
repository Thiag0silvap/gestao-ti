import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

const initialForm = {
  computer_id: "",
  asset_type: "",
  patrimony_number: "",
  serial_number: "",
  manufacturer: "",
  model: "",
  asset_status: "Ativo",
  sector: "",
  notes: "",
};

function Assets() {
  const [assets, setAssets] = useState([]);
  const [computers, setComputers] = useState([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [form, setForm] = useState(initialForm);
  const [editingId, setEditingId] = useState(null);

  const navigate = useNavigate();

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

  const loadAssets = () => {
    api.get("/assets")
      .then((response) => setAssets(response.data))
      .catch((error) => handleAuthError(error, "Erro ao carregar ativos"));
  };

  const loadComputers = () => {
    api.get("/computers")
      .then((response) => setComputers(response.data))
      .catch((error) => handleAuthError(error, "Erro ao carregar computadores"));
  };

  useEffect(() => {
    loadAssets();
    loadComputers();
  }, []);

  const assetTypes = useMemo(() => {
    const uniqueTypes = [...new Set(assets.map((a) => a.asset_type).filter(Boolean))];
    return uniqueTypes.sort((a, b) => a.localeCompare(b));
  }, [assets]);

  const assetStatuses = useMemo(() => {
    const uniqueStatuses = [...new Set(assets.map((a) => a.asset_status).filter(Boolean))];
    return uniqueStatuses.sort((a, b) => a.localeCompare(b));
  }, [assets]);

  const filteredAssets = useMemo(() => {
    return assets.filter((asset) => {
      const searchText = search.toLowerCase();

      const matchesSearch =
        asset.asset_type?.toLowerCase().includes(searchText) ||
        asset.patrimony_number?.toLowerCase().includes(searchText) ||
        asset.manufacturer?.toLowerCase().includes(searchText) ||
        asset.model?.toLowerCase().includes(searchText) ||
        asset.serial_number?.toLowerCase().includes(searchText);

      const matchesType = !typeFilter || asset.asset_type === typeFilter;
      const matchesStatus = !statusFilter || asset.asset_status === statusFilter;

      return matchesSearch && matchesType && matchesStatus;
    });
  }, [assets, search, typeFilter, statusFilter]);

  const getStatusClass = (status) => {
    if (status === "Ativo") return "bg-green-100 text-green-700";
    if (status === "Inativo") return "bg-red-100 text-red-700";
    if (status === "Manutenção") return "bg-yellow-100 text-yellow-700";
    return "bg-slate-200 text-slate-700";
  };

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
      computer_id: form.computer_id ? Number(form.computer_id) : null,
    };

    try {
      if (editingId) {
        await api.put(`/assets/${editingId}`, payload);
        alert("Ativo atualizado com sucesso!");
      } else {
        await api.post("/assets", payload);
        alert("Ativo cadastrado com sucesso!");
      }

      resetForm();
      loadAssets();
    } catch (error) {
      console.error(error);

      if (error.response?.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        navigate("/");
        return;
      }

      alert(error.response?.data?.detail || "Erro ao salvar ativo");
    }
  };

  const handleEdit = (asset) => {
    setEditingId(asset.id);
    setForm({
      computer_id: asset.computer_id ?? "",
      asset_type: asset.asset_type ?? "",
      patrimony_number: asset.patrimony_number ?? "",
      serial_number: asset.serial_number ?? "",
      manufacturer: asset.manufacturer ?? "",
      model: asset.model ?? "",
      asset_status: asset.asset_status ?? "Ativo",
      sector: asset.sector ?? "",
      notes: asset.notes ?? "",
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (assetId) => {
    const confirmed = window.confirm("Deseja realmente excluir este ativo?");

    if (!confirmed) return;

    try {
      await api.delete(`/assets/${assetId}`);
      alert("Ativo excluído com sucesso!");
      loadAssets();

      if (editingId === assetId) {
        resetForm();
      }
    } catch (error) {
      console.error(error);
      handleAuthError(error, "Erro ao excluir ativo");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-slate-800">Ativos</h2>
        <p className="text-slate-500">Lista de ativos vinculados ao inventário</p>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-xl font-bold text-slate-800">
          {editingId ? "Editar ativo" : "Cadastrar ativo"}
        </h3>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Computador vinculado
            </label>
            <select
              name="computer_id"
              value={form.computer_id}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            >
              <option value="">Nenhum</option>
              {computers.map((computer) => (
                <option key={computer.id} value={computer.id}>
                  {computer.hostname}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Tipo
            </label>
            <input
              type="text"
              name="asset_type"
              value={form.asset_type}
              onChange={handleChange}
              placeholder="Monitor, Nobreak, Impressora..."
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
              required
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Patrimônio
            </label>
            <input
              type="text"
              name="patrimony_number"
              value={form.patrimony_number}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Serial
            </label>
            <input
              type="text"
              name="serial_number"
              value={form.serial_number}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Fabricante
            </label>
            <input
              type="text"
              name="manufacturer"
              value={form.manufacturer}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Modelo
            </label>
            <input
              type="text"
              name="model"
              value={form.model}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Status
            </label>
            <select
              name="asset_status"
              value={form.asset_status}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            >
              <option value="Ativo">Ativo</option>
              <option value="Inativo">Inativo</option>
              <option value="Manutenção">Manutenção</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Setor
            </label>
            <input
              type="text"
              name="sector"
              value={form.sector}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div className="xl:col-span-3">
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Observações
            </label>
            <textarea
              name="notes"
              value={form.notes}
              onChange={handleChange}
              rows="3"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div className="flex gap-3 md:col-span-2 xl:col-span-3">
            <button
              type="submit"
              className="rounded-lg bg-slate-900 px-4 py-3 text-white hover:bg-slate-800"
            >
              {editingId ? "Salvar alterações" : "Cadastrar Ativo"}
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
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Buscar
            </label>
            <input
              type="text"
              placeholder="Tipo, patrimônio, fabricante..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Tipo
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            >
              <option value="">Todos</option>
              {assetTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            >
              <option value="">Todos</option>
              {assetStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => {
                setSearch("");
                setTypeFilter("");
                setStatusFilter("");
              }}
              className="w-full rounded-lg bg-slate-200 px-4 py-3 text-slate-800 hover:bg-slate-300"
            >
              Limpar filtros
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
        <table className="min-w-full">
          <thead className="bg-slate-100">
            <tr>
              <th className="px-4 py-3 text-left">Tipo</th>
              <th className="px-4 py-3 text-left">Patrimônio</th>
              <th className="px-4 py-3 text-left">Serial</th>
              <th className="px-4 py-3 text-left">Fabricante</th>
              <th className="px-4 py-3 text-left">Modelo</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Setor</th>
              <th className="px-4 py-3 text-left">Ações</th>
            </tr>
          </thead>
          <tbody>
            {filteredAssets.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-4 py-6 text-center text-slate-500">
                  Nenhum asset encontrado.
                </td>
              </tr>
            ) : (
              filteredAssets.map((asset) => (
                <tr key={asset.id} className="border-t border-slate-200">
                  <td className="px-4 py-3">{asset.asset_type || "-"}</td>
                  <td className="px-4 py-3">{asset.patrimony_number || "-"}</td>
                  <td className="px-4 py-3">{asset.serial_number || "-"}</td>
                  <td className="px-4 py-3">{asset.manufacturer || "-"}</td>
                  <td className="px-4 py-3">{asset.model || "-"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-3 py-1 text-sm font-medium ${getStatusClass(asset.asset_status)}`}
                    >
                      {asset.asset_status || "-"}
                    </span>
                  </td>
                  <td className="px-4 py-3">{asset.sector || "-"}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleEdit(asset)}
                        className="rounded-lg bg-blue-500 px-3 py-2 text-sm text-white hover:bg-blue-600"
                      >
                        Editar
                      </button>

                      <button
                        onClick={() => handleDelete(asset.id)}
                        className="rounded-lg bg-red-500 px-3 py-2 text-sm text-white hover:bg-red-600"
                      >
                        Excluir
                      </button>
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

export default Assets;