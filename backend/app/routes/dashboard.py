from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.asset import Asset
from app.models.computer import Computer
from app.models.user import User

router = APIRouter()


@router.get("/dashboard/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_computers = db.query(Computer).count()
    total_assets = db.query(Asset).count()

    recent_limit = datetime.now() - timedelta(days=7)

    online_recently = db.query(Computer).filter(
        Computer.last_seen != None,
        Computer.last_seen >= recent_limit
    ).count()

    offline_recently = db.query(Computer).filter(
        (Computer.last_seen == None) | (Computer.last_seen < recent_limit)
    ).count()

    monitors = db.query(Asset).filter(Asset.asset_type == "Monitor").count()
    nobreaks = db.query(Asset).filter(Asset.asset_type == "Nobreak").count()
    stabilizers = db.query(Asset).filter(Asset.asset_type == "Estabilizador").count()
    printers = db.query(Asset).filter(Asset.asset_type == "Impressora").count()

    return {
        "total_computers": total_computers,
        "online_recently": online_recently,
        "offline_recently": offline_recently,
        "total_assets": total_assets,
        "monitors": monitors,
        "nobreaks": nobreaks,
        "stabilizers": stabilizers,
        "printers": printers
    }