import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../api/api";

function ComputerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [computer, setComputer] = useState(null);
  const [assets, setAssets] = useState([]);

  useEffect(() => {
    api.get(`/computers/${id}`)
      .then((response) => setComputer(response.data))
      .catch((error) => {
        console.error(error);
        alert("Erro ao carregar detalhes do computador");
      });

    api.get(`/computers/${id}/assets`)
      .then((response) => setAssets(response.data))
      .catch((error) => {
        console.error(error);
        alert("Erro ao carregar assets do computador");
      });
  }, [id]);

  const formatDateTime = (value) => {
    if (!value) return "-";

    return new Date(value).toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  };

  const isOnlineRecently = useMemo(() => {
    if (!computer?.last_seen) return false;

    const lastSeen = new Date(computer.last_seen);
    const now = new Date();
    const diffMs = now - lastSeen;
    const diffDays = diffMs / (1000 * 60 * 60 * 24);

    return diffDays <= 7;
  }, [computer]);

  if (!computer) {
    return <p className="p-6 text-slate-600">Carregando detalhes...</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-3xl font-bold text-slate-800">
            {computer.hostname}
          </h2>
          <p className="text-slate-500">Detalhes do computador</p>
        </div>

        <div className="flex items-center gap-3">
          <span
            className={`rounded-full px-3 py-1 text-sm font-medium ${
              isOnlineRecently
                ? "bg-green-100 text-green-700"
                : "bg-red-100 text-red-700"
            }`}
          >
            {isOnlineRecently ? "Online recente" : "Offline"}
          </span>

          <button
            onClick={() => navigate("/computers")}
            className="rounded-lg bg-slate-200 px-4 py-2 text-slate-800 hover:bg-slate-300"
          >
            Voltar
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Usuário</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.user || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">IP</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.ip_address || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">MAC</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.mac_address || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">CPU</p>
          <h3 className="mt-2 text-xl font-semibold break-words">{computer.cpu || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">RAM</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.ram || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Disco</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.disk || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Sistema</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.os || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Fabricante</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.manufacturer || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Modelo</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.model || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Serial Number</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.serial_number || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Patrimônio</p>
          <h3 className="mt-2 text-xl font-semibold">{computer.patrimony_number || "-"}</h3>
        </div>

        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Último contato</p>
          <h3 className="mt-2 text-xl font-semibold">
            {formatDateTime(computer.last_seen)}
          </h3>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-sm">
        <h3 className="mb-4 text-2xl font-bold text-slate-800">Assets vinculados</h3>

        {assets.length === 0 ? (
          <p className="text-slate-500">Nenhum asset vinculado.</p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <table className="min-w-full">
              <thead className="bg-slate-100">
                <tr>
                  <th className="px-4 py-3 text-left">Tipo</th>
                  <th className="px-4 py-3 text-left">Patrimônio</th>
                  <th className="px-4 py-3 text-left">Fabricante</th>
                  <th className="px-4 py-3 text-left">Modelo</th>
                  <th className="px-4 py-3 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {assets.map((asset) => (
                  <tr key={asset.id} className="border-t border-slate-200">
                    <td className="px-4 py-3">{asset.asset_type}</td>
                    <td className="px-4 py-3">{asset.patrimony_number || "-"}</td>
                    <td className="px-4 py-3">{asset.manufacturer || "-"}</td>
                    <td className="px-4 py-3">{asset.model || "-"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-3 py-1 text-sm font-medium ${
                          asset.asset_status === "Ativo"
                            ? "bg-green-100 text-green-700"
                            : "bg-slate-200 text-slate-700"
                        }`}
                      >
                        {asset.asset_status || "-"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default ComputerDetail;