import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCurrentUser } from "../services/authService";

function Navbar() {
  const navigate = useNavigate();
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

  const handleLogout = () => {
  localStorage.removeItem("token");
  localStorage.removeItem("user");
  navigate("/");
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">
          Painel Administrativo
        </h1>

        {user && (
          <p className="text-sm text-slate-500">
            {user.name} ({user.role})
          </p>
        )}
      </div>

      <button
        onClick={handleLogout}
        className="rounded-lg bg-red-500 px-4 py-2 text-white hover:bg-red-600"
      >
        Sair
      </button>
    </header>
  );
}

export default Navbar;