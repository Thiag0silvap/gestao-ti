import { useCallback, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import api from "../api/api";
import TableControls from "../components/TableControls";
import { useUI } from "../components/UIProvider";
import useAutoRefresh from "../hooks/useAutoRefresh";
import useDataTable from "../hooks/useDataTable";
import { classifyHostSeverity, severityClassName, severityLabel } from "../utils/hostSeverity";

function Computers() {
  const [computers, setComputers] = useState([]);
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");
  const navigate = useNavigate();
  const { notify } = useUI();

  const loadComputers = useCallback(() => {
    api
      .get("/computers")
      .then((response) => setComputers(response.data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          navigate("/");
        } else {
          notify("Erro ao carregar computadores", "error");
        }
      });
  }, [navigate, notify]);

  useAutoRefresh(loadComputers);

  const sectors = useMemo(() => {
    const uniqueSectors = [...new Set(computers.map((c) => c.sector).filter(Boolean))];
    return uniqueSectors.sort((a, b) => a.localeCompare(b));
  }, [computers]);

  const formatDateTime = (value) => {
    if (!value) return "-";

    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  const filteredComputers = useMemo(() => {
    return computers.filter((computer) => {
      const searchText = search.toLowerCase();

      const matchesSearch =
        computer.hostname?.toLowerCase().includes(searchText) ||
        computer.user?.toLowerCase().includes(searchText) ||
        computer.ip_address?.toLowerCase().includes(searchText) ||
        computer.serial_number?.toLowerCase().includes(searchText);

      const matchesSector = !sectorFilter || computer.sector === sectorFilter;

      return matchesSearch && matchesSector;
    });
  }, [computers, search, sectorFilter]);

  const severitySummary = useMemo(() => (
    filteredComputers.reduce((summary, computer) => {
      const severity = classifyHostSeverity(computer);
      summary[severity] += 1;
      return summary;
    }, { healthy: 0, warning: 0, critical: 0, offline: 0 })
  ), [filteredComputers]);

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
  } = useDataTable(filteredComputers, {
    initialSort: { key: "hostname", direction: "asc" },
    accessors: {
      status: (computer) => {
        const severity = classifyHostSeverity(computer);
        return { critical: 3, warning: 2, offline: 1, healthy: 0 }[severity] ?? 0;
      },
      last_seen: (computer) => computer.last_seen || "",
    },
  });

  const getSortIndicator = (key) => {
    if (sortConfig?.key !== key) return "↕";
    return sortConfig.direction === "asc" ? "↑" : "↓";
  };

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="section-card">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            Mapa do parque
          </p>
          <h2 className="page-title mt-3 max-w-3xl">
            Pesquise, filtre e entre na ficha técnica de cada máquina.
          </h2>
          <p className="page-subtitle">
            Consulte inventário recente por hostname, usuário, IP, serial ou setor para ganhar
            contexto rápido antes do atendimento.
          </p>
        </div>

        <div className="section-card bg-[linear-gradient(180deg,rgba(255,255,255,0.88)_0%,rgba(243,248,245,0.92)_100%)]">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Total filtrado
              </p>
              <p className="mt-3 text-3xl font-semibold text-slate-900">{filteredComputers.length}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Saudáveis
              </p>
              <p className="mt-3 text-3xl font-semibold text-emerald-700">{severitySummary.healthy}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Atenção
              </p>
              <p className="mt-3 text-3xl font-semibold text-amber-700">{severitySummary.warning}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Críticos
              </p>
              <p className="mt-3 text-3xl font-semibold text-rose-700">{severitySummary.critical}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Offline
              </p>
              <p className="mt-3 text-3xl font-semibold text-slate-700">{severitySummary.offline}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section-card">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label className="field-label">Buscar</label>
            <input
              type="text"
              placeholder="Hostname, usuário, IP ou serial"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="field-input"
            />
          </div>

          <div>
            <label className="field-label">Setor</label>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="field-input"
            >
              <option value="">Todos os setores</option>
              {sectors.map((sector) => (
                <option key={sector} value={sector}>
                  {sector}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => {
                setSearch("");
                setSectorFilter("");
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
              <th><button type="button" onClick={() => requestSort("hostname")} className="table-sort-button">Equipamento <span className="table-sort-indicator">{getSortIndicator("hostname")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("user")} className="table-sort-button">Usuário <span className="table-sort-indicator">{getSortIndicator("user")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("ip_address")} className="table-sort-button">Rede <span className="table-sort-indicator">{getSortIndicator("ip_address")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("os")} className="table-sort-button">Plataforma <span className="table-sort-indicator">{getSortIndicator("os")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("sector")} className="table-sort-button">Setor <span className="table-sort-indicator">{getSortIndicator("sector")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("status")} className="table-sort-button">Status <span className="table-sort-indicator">{getSortIndicator("status")}</span></button></th>
              <th><button type="button" onClick={() => requestSort("last_seen")} className="table-sort-button">Último contato <span className="table-sort-indicator">{getSortIndicator("last_seen")}</span></button></th>
            </tr>
          </thead>
          <tbody>
            {totalItems === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-10 text-center text-slate-500">
                  Nenhum computador encontrado com os filtros atuais.
                </td>
              </tr>
            ) : (
              paginatedItems.map((computer) => (
                <tr key={computer.id}>
                  <td>
                    <div className="flex flex-col gap-1">
                      <Link to={`/computers/${computer.id}`} className="font-semibold text-emerald-700 hover:underline">
                        {computer.hostname}
                      </Link>
                      <span className="text-xs uppercase tracking-[0.16em] text-slate-400">
                        {computer.serial_number || "Sem serial"}
                      </span>
                    </div>
                  </td>
                  <td>{computer.user || "-"}</td>
                  <td>
                    <div className="flex flex-col gap-1">
                      <span>{computer.ip_address || "-"}</span>
                      <span className="text-xs text-slate-400">{computer.mac_address || "-"}</span>
                    </div>
                  </td>
                  <td>{computer.os || "-"}</td>
                  <td>{computer.sector || "-"}</td>
                  <td>
                    <span className={severityClassName(classifyHostSeverity(computer))}>
                      {severityLabel(classifyHostSeverity(computer))}
                    </span>
                  </td>
                  <td>{formatDateTime(computer.last_seen)}</td>
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
          itemLabel="computadores"
        />
      </section>
    </div>
  );
}

export default Computers;
