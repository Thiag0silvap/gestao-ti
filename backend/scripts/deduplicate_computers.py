import asyncio
import argparse
import sys
import os

# Adicionar o diretório base do backend ao PYTHONPATH
# O script está em backend/scripts/, então o base é o diretório pai
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

# Configurar ambiente se necessário (carregar .env manualmente se não estiver no context)
from dotenv import load_dotenv
load_dotenv(os.path.join(base_dir, ".env"))

from sqlalchemy import select, func
from app.database import AsyncSessionLocal, engine
from app.models.computer import Computer
from app.computer_identity import merge_duplicate_computers

async def deduplicate(dry_run=True):
    async with AsyncSessionLocal() as db:
        # 1. Agrupar por Hostname (desconsiderando case)
        # Hostname é o identificador mais comum que gera duplicidade visual
        print(f"{' [MODO SIMULAÇÃO - DRY RUN] ' if dry_run else ' [MODO EXECUÇÃO DEFINITIVA] '}")
        print("Iniciando análise de duplicados por Hostname...\n")
        
        # Subquery para encontrar hostnames duplicados
        stmt_dupes = select(func.lower(Computer.hostname)).group_by(func.lower(Computer.hostname)).having(func.count(Computer.id) > 1)
        result_dupes = await db.execute(stmt_dupes)
        duplicate_hostnames = [r[0] for r in result_dupes.all()]
        
        if not duplicate_hostnames:
            print("Nenhum duplicado encontrado por hostname.")
            return

        total_groups = len(duplicate_hostnames)
        total_removed = 0
        
        for i, hostname in enumerate(duplicate_hostnames, 1):
            # Buscar todos os registros com este hostname, ordenados pelo último visto (mais recente primeiro)
            stmt_all = select(Computer).filter(func.lower(Computer.hostname) == hostname.lower()).order_by(Computer.last_seen.desc(), Computer.id.desc())
            res_all = await db.execute(stmt_all)
            computers = res_all.scalars().all()
            
            if len(computers) < 2:
                continue
                
            primary = computers[0]
            to_merge = computers[1:]
            
            print(f"[{i}/{total_groups}] Hostname: {hostname.upper()}")
            print(f"  + Manter (Principal): ID {primary.id} | Setor: {primary.sector} | Visto em: {primary.last_seen}")
            
            for comp in to_merge:
                print(f"  - Mesclar (Duplicado): ID {comp.id} | Setor: {comp.sector} | Visto em: {comp.last_seen}")
            
            if not dry_run:
                try:
                    # merge_duplicate_computers já cuida de mover assets, tickets, etc e deletar o duplicado
                    count_merged = await merge_duplicate_computers(db, primary, to_merge)
                    await db.commit()
                    print(f"  => SUCESSO: {count_merged} registro(s) mesclado(s) no ID {primary.id}\n")
                    total_removed += count_merged
                except Exception as e:
                    await db.rollback()
                    print(f"  => ERRO ao mesclar: {e}\n")
            else:
                print(f"  => [SIMULAÇÃO] {len(to_merge)} registro(s) seriam mesclados no ID {primary.id}\n")
                total_removed += len(to_merge)

        print("-" * 50)
        print(f"Resumo Final:")
        print(f"Grupos de duplicados identificados: {total_groups}")
        print(f"Registros {'removidos/mesclados' if not dry_run else 'que seriam removidos'}: {total_removed}")
        print("-" * 50)
        
        if dry_run:
            print("\nPara executar as mudanças definitivamente, use: python scripts/deduplicate_computers.py --execute")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ferramenta de Deduplicação de Computadores - Gestão T.I")
    parser.add_argument("--execute", action="store_true", help="Executa as alterações no banco de dados. Sem esta flag, o script roda em modo simulação.")
    args = parser.parse_args()
    
    try:
        asyncio.run(deduplicate(dry_run=not args.execute))
    except KeyboardInterrupt:
        print("\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\nErro fatal na execução do script: {e}")
