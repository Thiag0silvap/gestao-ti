import { Link, useLocation } from "react-router-dom";

function Sidebar() {
  const location = useLocation();
  const userRaw = localStorage.getItem("user");
  const user = userRaw ? JSON.parse(userRaw) : null;

  const menu = [
    {
      name: "Dashboard",
      path: "/dashboard",
      roles: ["admin", "technician", "operator"],
    },
    {
      name: "Computadores",
      path: "/computers",
      roles: ["admin", "technician"],
    },
    {
      name: "Ativos",
      path: "/assets",
      roles: ["admin", "technician"],
    },
    {
      name: "Chamados",
      path: "/tickets",
      roles: ["admin", "technician", "operator"],
    },
    {
      name: "Usuários",
      path: "/users",
      roles: ["admin"],
    },
  ];

  const filteredMenu = menu.filter((item) =>
    user ? item.roles.includes(user.role) : false
  );

  return (
    <aside className="w-64 min-h-screen bg-slate-900 p-4 text-white">
      <h2 className="mb-8 text-2xl font-bold">Gestão TI</h2>

      <nav className="flex flex-col gap-2">
        {filteredMenu.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            className={`rounded-lg px-4 py-3 transition ${
              location.pathname === item.path
                ? "bg-slate-700"
                : "hover:bg-slate-800"
            }`}
          >
            {item.name}
          </Link>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;