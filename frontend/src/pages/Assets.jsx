import { useCallback, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/api";
import TableControls from "../components/TableControls";
import { useUI } from "../components/UIProvider";
import useAutoRefresh from "../hooks/useAutoRefresh";
import useDataTable from "../hooks/useDataTable";

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
  const { notify, confirm } = useUI();

  const upsertAsset = useCallback((assetData) => {
    setAssets((current) => {
      const exists = current.some((item) => item.id === assetData.id);
      if (exists) {
        return current.map((item) => (item.id === assetData.id ? assetData : item));
      }
      return [assetData, ...current];
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

  const loadAssets = useCallback(() => {
    api
      .get("/assets")
      .then((response) => setAssets(response.data))
      .catch((error) => handleAuthError(error, "Erro ao carregar ativos"));
  }, [navigate, notify]);

  const loadComputers = useCallback(() => {
    api
      .get("/computers")
      .then((response) => setComputers(response.data))
      .catch((error) => handleAuthError(error, "Erro ao carregar computadores"));
  }, [navigate, notify]);

  const refreshPage = useCallback(() => {
    loadAssets();
    loadComputers();
  }, [loadAssets, loadComputers]);

  useAutoRefresh(refreshPage);

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
    if (status === "Ativo") return "status-online";
    if (status === "Inativo") return "status-offline";
    if (status === "Manutenção") return "status-neutral";
    return "status-neutral";
  };

  const handleChange = (e) => {
    const { name, value } = e.target;

    setForm((prev) => {
      const next = {
        ...prev,
        [name]: value,
      };

      if (name === "computer_id") {
        const selectedComputer = computers.find((computer) => computer.id === Number(value));
        if (selectedComputer && !editingId) {
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
      computer_id: form.computer_id ? Number(form.computer_id) : null,
    };

    try {
      if (editingId) {
        const response = await api.put(`/assets/${editingId}`, payload);
        upsertAsset(response.data);
        notify("Ativo atualizado com sucesso!", "success");
      } else {
        const response = await api.post("/assets", payload);
        upsertAsset(response.data);
        notify("Ativo cadastrado com sucesso!", "success");
      }

      resetForm();
    } catch (error) {
      console.error(error);

      if (error.response?.status === 401) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
        navigate("/");
        return;
      }

      notify(error.response?.data?.detail || "Erro ao salvar ativo", "error");
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
    const confirmed = await confirm({
      title: "Excluir ativo",
      message: "Deseja realmente excluir este ativo? Esta acao nao pode ser desfeita.",
      confirmLabel: "Excluir",
      cancelLabel: "Cancelar",
      tone: "danger",
    });

    if (!confirmed) return;

    try {
      await api.delete(`/assets/${assetId}`);
      setAssets((current) => current.filter((asset) => asset.id !== assetId));
      notify("Ativo excluido com sucesso!", "success");

      if (editingId === assetId) {
        resetForm();
      }
    } catch (error) {
      console.error(error);
      handleAuthError(error, "Erro ao excluir ativo");
    }
  };

  const activeAssets = filteredAssets.filter((asset) => asset.asset_status === "Ativo").length;

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
  } = useDataTable(filteredAssets, {
    initialSort: { key: "asset_type", direction: "asc" },
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
            Patrimonio operacional
          </p>
          <h2 className="page-title mt-3 text-3xl md:text-[2.6rem]">
            Organize perifericos e equipamentos vinculados ao inventario.
          </h2>
          <p className="page-subtitle">
            Centralize os ativos por tipo, setor, patrimonio e situacao para melhorar rastreabilidade.
          </p>
        </div>

        <div className="section-card">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Total</p>
              <p className="mt-3 text-3xl font-semibold text-slate-900">{filteredAssets.length}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Ativos</p>
              <p className="mt-3 text-3xl font-semibold text-emerald-700">{activeAssets}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tipos</p>
              <p className="mt-3 text-3xl font-semibold text-amber-700">{assetTypes.length}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Cadastro</p>
            <h3 className="mt-2 font-[var(--font-display)] text-3xl font-semibold text-slate-900">
              {editingId ? "Editar ativo" : "Cadastrar novo ativo"}
            </h3>
          </div>
          <p className="text-sm text-slate-500">
            Vincule ao computador sempre que o item fizer parte da estacao.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          <div>
            <label className="field-label">Computador vinculado</label>
            <select name="computer_id" value={form.computer_id} onChange={handleChange} className="field-input">
              <option value="">Nenhum</option>
              {computers.map((computer) => (
                <option key={computer.id} value={computer.id}>
                  {computer.hostname}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="field-label">Tipo</label>
            <input type="text" name="asset_type" value={form.asset_type} onChange={handleChange} placeholder="Monitor, Nobreak, Impressora..." className="field-input" required />
          </div>

          <div>
            <label className="field-label">Patrimonio</label>
            <input type="text" name="patrimony_number" value={form.patrimony_number} onChange={handleChange} className="field-input" />
          </div>

          <div>
            <label className="field-label">Serial</label>
            <input type="text" name="serial_number" value={form.serial_number} onChange={handleChange} className="field-input" />
          </div>

          <div>
            <label className="field-label">Fabricante</label>
            <input type="text" name="manufacturer" value={form.manufacturer} onChange={handleChange} className="field-input" />
          </div>

          <div>
            <label className="field-label">Modelo</label>
            <input type="text" name="model" value={form.model} onChange={handleChange} className="field-input" />
          </div>

          <div>
            <label className="field-label">Status</label>
            <select name="asset_status" value={form.asset_status} onChange={handleChange} className="field-input">
              <option value="Ativo">Ativo</option>
              <option value="Inativo">Inativo</option>
              <option value="Manutenção">Manutenção</option>
            </select>
          </div>

          <div>
            <label className="field-label">Setor</label>
            <input type="text" name="sector" value={form.sector} onChange={handleChange} className="field-input" />
          </div>

          <div className="xl:col-span-3">
            <label className="field-label">Observacoes</label>
            <textarea name="notes" value={form.notes} onChange={handleChange} rows="3" className="field-input" />
          </div>

          <div className="flex flex-wrap gap-3 md:col-span-2 xl:col-span-3">
            <button type="submit" className="btn-primary">
              {editingId ? "Salvar alteracoes" : "Cadastrar ativo"}
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
          <div>
            <label className="field-label">Buscar</label>
            <input type="text" placeholder="Tipo, patrimonio, fabricante..." value={search} onChange={(e) => setSearch(e.target.value)} className="field-input" />
          </div>

          <div>
            <label className="field-label">Tipo</label>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="field-input">
              <option value="">Todos</option>
              {assetTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="field-label">Status</label>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="field-input">
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
              className="btn-secondary w-full"
            >
              Limpar filtros
            </button>
          </div>
        </div>
      </section>

      <section className="table-shell">
        <table>
          <thead>
            <tr>
              <th><button type="button" onClick={() => requestSort("asset_type")} className="table-sort-button">Tipo <span className="table-sort-indicator">{getSortIndicator("asset_type")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("patrimony_number")} className="table-sort-button">Patrimonio <span className="table-sort-indicator">{getSortIndicator("patrimony_number")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("serial_number")} className="table-sort-button">Serial <span className="table-sort-indicator">{getSortIndicator("serial_number")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("manufacturer")} className="table-sort-button">Fabricante <span className="table-sort-indicator">{getSortIndicator("manufacturer")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("model")} className="table-sort-button">Modelo <span className="table-sort-indicator">{getSortIndicator("model")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("asset_status")} className="table-sort-button">Status <span className="table-sort-indicator">{getSortIndicator("asset_status")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("sector")} className="table-sort-button">Setor <span className="table-sort-indicator">{getSortIndicator("sector")}</span></button></th>
              <th>Acoes</th>
            </tr>
          </thead>
          <tbody>
            {totalItems === 0 ? (
              <tr>
                <td colSpan="8" className="px-4 py-10 text-center text-slate-500">
                  Nenhum ativo encontrado.
                </td>
              </tr>
            ) : (
              paginatedItems.map((asset) => (
                <tr key={asset.id}>
                  <td>{asset.asset_type || "-"}</td>
                  <td>{asset.patrimony_number || "-"}</td>
                  <td>{asset.serial_number || "-"}</td>
                  <td>{asset.manufacturer || "-"}</td>
                  <td>{asset.model || "-"}</td>
                  <td>
                    <span className={getStatusClass(asset.asset_status)}>{asset.asset_status || "-"}</span>
                  </td>
                  <td>{asset.sector || "-"}</td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      <button onClick={() => handleEdit(asset)} className="btn-secondary px-3 py-2 text-sm">
                        Editar
                      </button>
                      <button onClick={() => handleDelete(asset.id)} className="btn-danger px-3 py-2 text-sm">
                        Excluir
                      </button>
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
          itemLabel="ativos"
        />
      </section>
    </div>
  );
}

export default Assets;
