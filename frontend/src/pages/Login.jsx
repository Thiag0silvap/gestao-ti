import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api/api";

function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  const handleLogin = async (e) => {
  e.preventDefault();

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
    alert("Usuário ou senha inválidos");
  }
};

  return (
    <div style={{ padding: "40px" }}>
      <h1>Gestão de TI</h1>
      <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "10px", maxWidth: "300px" }}>
        <input
          type="text"
          placeholder="Usuário"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="Senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Entrar</button>
      </form>
    </div>
  );
}

export default Login;