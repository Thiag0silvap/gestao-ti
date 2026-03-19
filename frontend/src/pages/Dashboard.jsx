import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/dashboard/summary")
      .then((response) => setData(response.data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          navigate("/");
        } else {
          alert("Erro ao carregar dashboard");
        }
      });
  }, [navigate]);

  if (!data) {
    return <p className="p-10 text-slate-600">Carregando...</p>;
  }

  const cards = [
    { title: "Computadores", value: data.total_computers },
    { title: "Online", value: data.online_recently },
    { title: "Offline", value: data.offline_recently },
    { title: "Ativos", value: data.total_assets },
    { title: "Monitores", value: data.monitors },
    { title: "Nobreaks", value: data.nobreaks },
    { title: "Estabilizadores", value: data.stabilizers },
    { title: "Impressoras", value: data.printers },
  ];

  return (
    <div>
      <h2 className="mb-6 text-3xl font-bold text-slate-800">Dashboard</h2>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.title} className="rounded-2xl bg-white p-5 shadow-sm">
            <p className="text-sm text-slate-500">{card.title}</p>
            <h3 className="mt-2 text-3xl font-bold text-slate-800">{card.value}</h3>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Dashboard;