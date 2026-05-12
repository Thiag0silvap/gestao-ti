from datetime import datetime, timedelta
from sqlalchemy import func, select, case, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.computer import Computer
from app.models.ticket import Ticket

# Critério consistente com app/monitoring.py
OFFLINE_THRESHOLD = timedelta(hours=24)


class MetricsService:

    @staticmethod
    async def get_operational_metrics(db: AsyncSession, start_time: datetime) -> dict:
        """
        Consolida métricas operacionais do sistema via queries leves e otimizadas.
        Sem carregar objetos completos na memória.
        """
        now = datetime.now()
        online_cutoff = now - OFFLINE_THRESHOLD

        # ─── 1. Métricas de Computadores/Agentes ──────────────────────────────
        # Uma única query com COUNT condicional (CASE WHEN) para online/offline/sem_versao
        agent_query = await db.execute(
            select(
                func.count(Computer.id).label("total"),
                func.count(
                    case(
                        (Computer.last_seen >= online_cutoff, Computer.id),
                        else_=None
                    )
                ).label("online"),
                func.count(
                    case(
                        (
                            or_(
                                Computer.last_seen < online_cutoff,
                                Computer.last_seen.is_(None)
                            ),
                            Computer.id
                        ),
                        else_=None
                    )
                ).label("offline"),
                func.count(
                    case(
                        (Computer.agent_version.is_(None), Computer.id),
                        else_=None
                    )
                ).label("sem_versao"),
            )
        )
        agent_row = agent_query.one()

        # ─── 2. Agrupamento de versões dos agentes ────────────────────────────
        version_query = await db.execute(
            select(
                Computer.agent_version,
                func.count(Computer.id).label("total")
            )
            .where(Computer.agent_version.isnot(None))
            .group_by(Computer.agent_version)
            .order_by(func.count(Computer.id).desc())
        )
        versions = {row.agent_version: row.total for row in version_query.all()}

        # ─── 3. Métricas de Chamados (por status) ────────────────────────────
        ticket_query = await db.execute(
            select(
                Ticket.status,
                func.count(Ticket.id).label("total")
            )
            .group_by(Ticket.status)
        )
        ticket_counts = {row.status: row.total for row in ticket_query.all()}

        tickets_abertos = ticket_counts.get("Aberto", 0)
        tickets_em_andamento = ticket_counts.get("Em Andamento", 0)
        tickets_resolvidos = ticket_counts.get("Resolvido", 0)
        tickets_fechados = ticket_counts.get("Fechado", 0)
        tickets_ativos = tickets_abertos + tickets_em_andamento

        # ─── 4. Alertas Críticos (replicando lógica de monitoring.py via SQL) ─
        # Crítico: cpu >= 90 OR memory >= 90 OR disk_free <= 10
        # Warning:  cpu >= 75 OR memory >= 80 OR disk_free <= 20
        critico_query = await db.execute(
            select(func.count(Computer.id)).where(
                and_(
                    Computer.last_seen >= online_cutoff,  # só conta máquinas online
                    or_(
                        Computer.cpu_usage_percent >= 90,
                        Computer.memory_usage_percent >= 90,
                        Computer.disk_free_percent <= 10,
                    )
                )
            )
        )
        alertas_criticos = critico_query.scalar() or 0

        warning_query = await db.execute(
            select(func.count(Computer.id)).where(
                and_(
                    Computer.last_seen >= online_cutoff,
                    or_(
                        Computer.cpu_usage_percent >= 75,
                        Computer.memory_usage_percent >= 80,
                        Computer.disk_free_percent <= 20,
                    )
                )
            )
        )
        alertas_warning = warning_query.scalar() or 0

        # ─── 5. Uptime ────────────────────────────────────────────────────────
        uptime_delta = now - start_time
        uptime_seconds = int(uptime_delta.total_seconds())

        return {
            "timestamp": now.isoformat(),
            "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(uptime_delta).split(".")[0],
            "agents": {
                "total_computers": agent_row.total,
                "online": agent_row.online,
                "offline": agent_row.offline,
                "sem_versao": agent_row.sem_versao,
                "online_threshold_hours": int(OFFLINE_THRESHOLD.total_seconds() / 3600),
                "versions": versions,
            },
            "tickets": {
                "abertos": tickets_abertos,
                "em_andamento": tickets_em_andamento,
                "resolvidos": tickets_resolvidos,
                "fechados": tickets_fechados,
                "ativos_total": tickets_ativos,
            },
            "alerts": {
                "criticos": alertas_criticos,
                "warnings": alertas_warning,
                "note": "Conta apenas maquinas online com métricas criticas/warning"
            }
        }
