# Backend Gestao TI

## Objetivo

Subir a API FastAPI de forma acessivel na rede local, sem ficar presa a `localhost`.

## Configuracao

1. Copie `.env.example` para `.env`.
2. Ajuste os dados do SQL Server.
3. Defina:

- `API_HOST=0.0.0.0` para aceitar conexoes da rede local.
- `API_PORT=8000` ou outra porta livre.
- `BACKEND_CORS_ORIGINS` com os enderecos do frontend que vao acessar a API.

Exemplo de origem do frontend:

```text
http://192.168.0.10:5173
```

## Subir a API

```powershell
python run_api.py
```

## Testes na rede local

Com a API rodando, teste na propria maquina:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

Depois teste pelo IP da maquina servidora:

```powershell
Invoke-WebRequest http://SEU-IP:8000/health
```

## Importante

- Se outra maquina nao acessar, verifique o firewall do Windows e libere a porta da API.
- O banco pode continuar local nessa maquina. As outras estacoes falam apenas com a API.
- O agente remoto deve usar `API_URL=http://SEU-IP:8000/agent/computers/sync`.
