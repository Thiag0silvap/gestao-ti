# Agente de Inventario

Agente Python para coletar informacoes basicas da maquina Windows e sincronizar com a API do projeto.

## O que ele coleta

- Hostname
- Usuario logado
- IP local
- MAC address
- CPU
- RAM
- Disco
- Sistema operacional
- Fabricante
- Modelo
- Numero de serie

## Preparacao

1. Instale Python 3.11 ou superior na maquina.
2. Copie `.env.example` para `.env`.
3. Ajuste `API_URL` e `AGENT_API_KEY`.
4. Instale as dependencias:

```powershell
pip install -r requirements.txt
```

## Teste local

Coleta os dados e mostra no log sem enviar nada:

```powershell
python inventory_agent.py --once --dry-run
```

Faz uma unica sincronizacao real:

```powershell
python inventory_agent.py --once
```

Modo continuo:

```powershell
python inventory_agent.py
```

Logs detalhados:

```powershell
python inventory_agent.py --once --debug
```

## Gerar EXE

Se o PyInstaller estiver instalado na maquina de build:

```powershell
build_exe.bat
```

O executavel sera criado em:

```text
agent\dist\InventoryAgent.exe
```

O build atual gera o agente sem console, pensado para rodar em segundo plano no Windows.

Para distribuir em outra maquina, envie:

- `InventoryAgent.exe`
- um arquivo `.env` no mesmo diretorio do `.exe`
- `install_agent.cmd`
- `uninstall_agent.cmd`

Exemplo de `.env` para a maquina cliente:

```env
API_URL=http://SEU-IP:8000/agent/computers/sync
AGENT_API_KEY=troque-esta-chave
INTERVAL_SECONDS=300
REQUEST_TIMEOUT_SECONDS=15
DEFAULT_SECTOR=TI
PATRIMONY_NUMBER=
EQUIPMENT_STATUS=Ativo
AGENT_NOTES=Cadastro automatico pelo agente
VERIFY_SSL=true
```

Teste do executavel:

```powershell
InventoryAgent.exe --once --dry-run
InventoryAgent.exe --once
```

## Iniciar com o Windows

Depois de copiar o agente para a maquina do colaborador e ajustar o `.env`, basta executar:

```powershell
install_agent.cmd
```

Esse arquivo:

- pergunta o setor da maquina na hora da instalacao
- atualiza `DEFAULT_SECTOR` no `.env`
- registra a inicializacao automatica para voce

Se preferir manualmente, ainda funciona assim:

```powershell
cd agent
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
```

Isso cria uma tarefa chamada `GestaoTI-InventoryAgent` para iniciar no logon e na inicializacao do Windows.

Se preferir usar o Python do `.venv` em vez do executavel:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1 -UsePythonScript
```

Para remover depois:

```powershell
uninstall_agent.cmd
```

Os logs ficam em:

```text
agent\logs\inventory_agent.log
```

## Observacoes

- O agente tenta usar `wmic` e faz fallback para `Get-CimInstance` quando necessario.
- `INTERVAL_SECONDS` minimo aceito: `30`.
- `REQUEST_TIMEOUT_SECONDS` minimo aceito: `5`.
- Se a API usar HTTPS com certificado interno temporariamente, voce pode testar com `VERIFY_SSL=false`.
- Para producao, prefira manter `VERIFY_SSL=true`.
