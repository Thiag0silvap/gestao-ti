import { useState } from "react";
import { useNavigate } from "react-router-dom";

import api from "../api/api";

function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMessage("");

    const formData = new URLSearchParams();
    formData.append("username", username);
    formData.append("password", password);

    try {
      const response = await api.post("/auth/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      localStorage.setItem("token", response.data.access_token);

      const meResponse = await api.get("/users/me", {
        headers: {
          Authorization: `Bearer ${response.data.access_token}`,
        },
      });

      localStorage.setItem("user", JSON.stringify(meResponse.data));
      navigate("/dashboard");
    } catch (error) {
      console.error(error);
      setErrorMessage("Usuário ou senha inválidos. Confira os dados e tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(31,122,90,0.24),_transparent_32%),linear-gradient(135deg,_#f6f1e7_0%,_#e9e0cd_45%,_#d4dccf_100%)]">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(24,49,43,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(24,49,43,0.05)_1px,transparent_1px)] bg-[size:42px_42px]" />

      <div className="relative z-10 grid min-h-screen w-full grid-cols-1 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="flex items-center px-6 py-12 md:px-10 xl:px-20">
          <div className="max-w-xl">
            <p className="text-sm font-semibold uppercase tracking-[0.34em] text-emerald-900/60">
              Plataforma operacional
            </p>
            <h1 className="mt-5 font-[var(--font-display)] text-[3.2rem] font-semibold leading-[1.05] text-slate-900 md:text-[4.1rem]">
              Atlas mantém o inventário vivo e o suporte centralizado.
            </h1>
            <p className="mt-6 text-lg leading-8 text-slate-700">
              Consolide computadores, ativos, chamados e usuários em um painel mais
              claro para a equipe técnica e para a operação do dia a dia.
            </p>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {[
                ["Inventário contínuo", "Agente envia dados atualizados das máquinas"],
                ["Chamados ligados ao equipamento", "Atendimento com contexto técnico"],
                ["Controle de perfis", "Acesso por função e responsabilidade"],
              ].map(([title, description]) => (
                <div key={title} className="glass-panel p-4">
                  <p className="text-sm font-semibold text-slate-800">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="flex items-center justify-center px-6 py-12 md:px-10">
          <div className="w-full max-w-md rounded-[32px] border border-white/60 bg-white/78 p-7 shadow-[0_30px_60px_rgba(17,32,29,0.18)] backdrop-blur-xl md:p-8">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">
                Acesso seguro
              </p>
              <h2 className="mt-3 font-[var(--font-display)] text-[2.2rem] font-semibold text-slate-900">
                Entrar no painel
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Use seu usuário institucional para acessar o ambiente operacional.
              </p>
            </div>

            <form onSubmit={handleLogin} className="mt-8 space-y-4">
              <div>
                <label className="field-label">Usuário</label>
                <input
                  type="text"
                  placeholder="Digite seu usuário"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="field-input"
                  required
                />
              </div>

              <div>
                <label className="field-label">Senha</label>
                <input
                  type="password"
                  placeholder="Digite sua senha"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-input"
                  required
                />
              </div>

              {errorMessage && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {errorMessage}
                </div>
              )}

              <button type="submit" className="btn-primary w-full" disabled={loading}>
                {loading ? "Validando acesso..." : "Entrar no sistema"}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}

export default Login;
