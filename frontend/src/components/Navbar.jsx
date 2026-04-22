import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { getCurrentUser } from "../services/authService";

const titles = {
  "/dashboard": {
    title: "Visão operacional",
    subtitle: "Acompanhe o parque de TI, a atividade recente dos equipamentos e o ritmo do suporte.",
  },
  "/computers": {
    title: "Inventário de computadores",
    subtitle: "Consulte máquinas, status recente, dados técnicos e relação com os ativos.",
  },
  "/alerts": {
    title: "Alertas ativos",
    subtitle: "Veja rapidamente o que exige resposta da equipe antes de virar incidente maior.",
  },
  "/assets": {
    title: "Controle de ativos",
    subtitle: "Gerencie monitores, nobreaks, impressoras e outros itens vinculados ao inventário.",
  },
  "/tickets": {
    title: "Central de chamados",
    subtitle: "Organize demandas, acompanhe prioridades e distribua atendimentos com clareza.",
  },
  "/users": {
    title: "Gestão de usuários",
    subtitle: "Controle acessos, perfis e a disponibilidade das contas do sistema.",
  },
};

function Navbar({ onOpenSidebar }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [user, setUser] = useState(null);

  useEffect(() => {
    getCurrentUser()
      .then((data) => setUser(data))
      .catch((error) => {
        console.error(error);

        if (error.response?.status === 401) {
          localStorage.removeItem("token");
          localStorage.removeItem("user");
          navigate("/");
        }
      });
  }, [navigate]);

  const pageMeta = useMemo(() => {
    if (location.pathname.startsWith("/computers/")) {
      return {
        title: "Ficha do equipamento",
        subtitle: "Detalhes técnicos, último contato e ativos associados a esta máquina.",
      };
    }

    return (
      titles[location.pathname] || {
        title: "Atlas",
        subtitle: "Painel central do ambiente de suporte, inventário e monitoramento.",
      }
    );
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    navigate("/");
  };

  return (
    <header className="px-4 pt-4 md:px-6 md:pt-6 xl:px-8">
      <div className="glass-panel flex flex-col gap-5 px-5 py-5 md:px-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-4">
          <button
            type="button"
            onClick={onOpenSidebar}
            className="btn-secondary h-12 w-12 shrink-0 px-0 lg:hidden"
            aria-label="Abrir menu"
          >
            <span className="text-xl leading-none">≡</span>
          </button>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
              Atlas
            </p>
            <h1 className="mt-2 font-[var(--font-display)] text-[1.95rem] font-semibold text-slate-900 md:text-[2.2rem]">
              {pageMeta.title}
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-600">
              {pageMeta.subtitle}
            </p>
          </div>
        </div>

        <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
          {user && (
            <div className="rounded-3xl border border-white/70 bg-white/70 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
                Sessão ativa
              </p>
              <p className="mt-1 text-sm font-semibold text-slate-800">{user.name}</p>
              <p className="text-sm text-slate-500">
                {user.role} {user.sector ? `• ${user.sector}` : ""}
              </p>
            </div>
          )}

          <button onClick={handleLogout} className="btn-danger">
            Encerrar sessão
          </button>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
