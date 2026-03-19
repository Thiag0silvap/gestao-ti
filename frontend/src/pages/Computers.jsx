import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../api/api";

function Computers() {
  const [computers, setComputers] = useState([]);
  const [search, setSearch] = useState("");
  const [sectorFilter, setSectorFilter] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    api.get("/computers")
      .then((response) => setComputers(response.data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          navigate("/");
        } else {
          alert("Erro ao carregar computadores");
        }
      });
  }, [navigate]);

  const sectors = useMemo(() => {
    const uniqueSectors = [...new Set(computers.map((c) => c.sector).filter(Boolean))];
    return uniqueSectors.sort((a, b) => a.localeCompare(b));
  }, [computers]);

  const isOnlineRecently = (lastSeen) => {
    if (!lastSeen) return false;

    const lastSeenDate = new Date(lastSeen);
    const now = new Date();
    const diffMs = now - lastSeenDate;
    const diffDays = diffMs / (1000 * 60 * 60 * 24);

    return diffDays <= 7;
  };

  const formatDateTime = (value) => {
    if (!value) return "-";

    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  const filteredComputers = useMemo(() => {
    return computers.filter((computer) => {
      const matchesSearch =
        computer.hostname?.toLowerCase().includes(search.toLowerCase()) ||
        computer.user?.toLowerCase().includes(search.toLowerCase()) ||
        computer.ip_address?.toLowerCase().includes(search.toLowerCase());

      const matchesSector =
        !sectorFilter || computer.sector === sectorFilter;

      return matchesSearch && matchesSector;
    });
  }, [computers, search, sectorFilter]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-800">Computadores</h2>
          <p className="text-slate-500">Lista de computadores inventariados</p>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Buscar
            </label>
            <input
              type="text"
              placeholder="Buscar por hostname, usuário ou IP"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-600">
              Setor
            </label>
            <select
              value={sectorFilter}
              onChange={(e) => setSectorFilter(e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-4 py-3 outline-none focus:border-slate-500"
            >
              <option value="">Todos</option>
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
              <th className="px-4 py-3 text-left">Hostname</th>
              <th className="px-4 py-3 text-left">IP</th>
              <th className="px-4 py-3 text-left">Usuário</th>
              <th className="px-4 py-3 text-left">Sistema</th>
              <th className="px-4 py-3 text-left">Setor</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Último contato</th>
            </tr>
          </thead>
          <tbody>
            {filteredComputers.length === 0 ? (
              <tr>
                <td colSpan="7" className="px-4 py-6 text-center text-slate-500">
                  Nenhum computador encontrado.
                </td>
              </tr>
            ) : (
              filteredComputers.map((computer) => (
                <tr key={computer.id} className="border-t border-slate-200">
                  <td className="px-4 py-3">
                    <Link
                      to={`/computers/${computer.id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {computer.hostname}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{computer.ip_address || "-"}</td>
                  <td className="px-4 py-3">{computer.user || "-"}</td>
                  <td className="px-4 py-3">{computer.os || "-"}</td>
                  <td className="px-4 py-3">{computer.sector || "-"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-3 py-1 text-sm font-medium ${
                        isOnlineRecently(computer.last_seen)
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {isOnlineRecently(computer.last_seen)
                        ? "Online recente"
                        : "Offline"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {formatDateTime(computer.last_seen)}
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

export default Computers;