"""User request 2026-11-06: delete every project except the one linked to the
'martin' bid (Luthar), and every bid (CRM opportunity) except 'martin'.
Backup first: C:/Users/ishat/Downloads/OE-db-backups/before-delete-2026-11-06.dump
Run with --apply to commit; otherwise a dry run (rolled back)."""
import asyncio, os, sys, uuid
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres@127.0.0.1:60481/postgres")
os.environ.setdefault("DATABASE_SYNC_URL", "postgresql+psycopg2://postgres@127.0.0.1:60481/postgres")
sys.path.insert(0, r"C:\Users\ishat\Downloads\OpenConstructionERP-main (2)\OpenConstructionERP-main\backend")
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import importlib, pkgutil
import app.modules as _mods
for _m in pkgutil.iter_modules(_mods.__path__):
    try:
        importlib.import_module(f"app.modules.{_m.name}.models")
    except ModuleNotFoundError:
        pass
    except Exception as _e:  # a broken optional module must not stop the run
        print("skip models of", _m.name, type(_e).__name__)
from app.modules.projects.models import Project
from app.modules.projects.service import purge_project_children_without_cascade
from app.modules.crm.models import Opportunity
from app.modules.crm.service import CrmService

APPLY = "--apply" in sys.argv

async def main():
    eng = create_async_engine(os.environ["DATABASE_URL"])
    async with AsyncSession(eng, expire_on_commit=False) as s:
        async with s.begin():
            martin = (await s.execute(select(Opportunity).where(func.lower(Opportunity.title) == "martin"))).scalars().all()
            assert len(martin) == 1, f"expected one 'martin' bid, found {len(martin)}"
            keep_opp = martin[0].id
            keep_proj = martin[0].project_id
            projects = (await s.execute(select(Project))).scalars().all()
            print("keep bid:", keep_opp, "| keep project:", keep_proj, [p.name for p in projects if str(p.id) == str(keep_proj)])
            drop_proj = [p.id for p in projects if str(p.id) != str(keep_proj)]
            print("projects to delete:", [(str(p.id), p.name) for p in projects if p.id in drop_proj])
            opps = (await s.execute(select(Opportunity.id).where(Opportunity.id != keep_opp))).scalars().all()
            print("bids to delete:", len(opps))
            svc = CrmService(s)
            for oid in opps:
                await svc.delete_opportunity(oid)
            if drop_proj:
                await purge_project_children_without_cascade(s, drop_proj)
                r = await s.execute(delete(Project).where(Project.id.in_(drop_proj)))
                print("projects deleted:", r.rowcount)
            await s.flush()
            left_p = (await s.execute(select(Project.name))).scalars().all()
            left_o = (await s.execute(select(Opportunity.title))).scalars().all()
            print("left projects:", left_p, "| left bids:", left_o)
            if not APPLY:
                print("DRY RUN - rolling back")
                await s.rollback()
                return
        print("COMMITTED")
    await eng.dispose()

asyncio.run(main())
