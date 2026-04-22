import { Link, useLocation } from "react-router-dom";

import { getStoredUser } from "../services/sessionService";

const menu = [
  {
    name: "Dashboard",
    path: "/dashboard",
    description: "Indicadores gerais",
    icon: "D",
    roles: ["admin", "technician", "operator"],
  },
  {
    name: "Computadores",
    path: "/computers",
    description: "Inventário técnico",
    icon: "C",
    roles: ["admin", "technician"],
  },
  {
    name: "Alertas",
    path: "/alerts",
    description: "Prioridades ativas",
    icon: "!",
    roles: ["admin", "technician"],
  },
  {
    name: "Ativos",
    path: "/assets",
    description: "Periféricos e itens",
    icon: "A",
    roles: ["admin", "technician"],
  },
  {
    name: "Chamados",
    path: "/tickets",
    description: "Fluxo de suporte",
    icon: "T",
    roles: ["admin", "technician", "operator"],
  },
  {
    name: "Usuários",
    path: "/users",
    description: "Perfis e acessos",
    icon: "U",
    roles: ["admin"],
  },
];

function Sidebar({ isOpen, onClose }) {
  const location = useLocation();
  const user = getStoredUser();

  const filteredMenu = menu.filter((item) => (user ? item.roles.includes(user.role) : false));

  return (
    <>
      <div
        className={`fixed inset-0 z-30 bg-slate-950/40 backdrop-blur-sm transition lg:hidden ${
          isOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0"
        }`}
        onClick={onClose}
      />

      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-[274px] flex-col border-r border-white/10 bg-[linear-gradient(180deg,#18312b_0%,#11201d_100%)] p-4 text-white shadow-2xl transition-transform duration-300 lg:sticky lg:top-0 lg:z-20 lg:min-h-screen lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-200/70">
              Monitoramento
            </p>
            <h2 className="mt-2 font-[var(--font-display)] text-[1.9rem] font-semibold">
              Atlas
            </h2>
            <p className="mt-2 text-sm leading-6 text-emerald-50/70">
              Inventário, alertas e operação em um painel mais leve para a equipe.
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white/80 lg:hidden"
          >
            Fechar
          </button>
        </div>

        <div className="mt-6 rounded-[24px] border border-white/10 bg-white/5 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100/50">
            Sessão
          </p>
          <p className="mt-2 text-sm text-white/85">{user?.name || "Usuário"}</p>
          <p className="text-sm text-emerald-100/60">
            {user?.role || "-"} {user?.sector ? `• ${user.sector}` : ""}
          </p>
        </div>

        <nav className="mt-6 flex flex-1 flex-col gap-2">
          {filteredMenu.map((item) => {
            const isActive =
              location.pathname === item.path ||
              (item.path === "/computers" && location.pathname.startsWith("/computers/"));

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`group rounded-[20px] border px-4 py-3 transition ${
                  isActive
                    ? "border-emerald-200/20 bg-emerald-100/10 text-white shadow-lg"
                    : "border-transparent bg-white/0 text-white/72 hover:border-white/10 hover:bg-white/6 hover:text-white"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex h-9 w-9 items-center justify-center rounded-2xl text-sm ${
                      isActive ? "bg-emerald-200/20 text-emerald-50" : "bg-white/8 text-white/70"
                    }`}
                  >
                    {item.icon}
                  </span>

                  <div>
                    <p className="text-[15px] font-medium">{item.name}</p>
                    <p className="text-[13px] text-white/55 group-hover:text-white/72">
                      {item.description}
                    </p>
                  </div>
                </div>
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}

export default Sidebar;
