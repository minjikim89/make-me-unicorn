import json
import pickle

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, User
from app.security import current_user

router = APIRouter()


@router.get("/json")
def export_json(db: Session = Depends(get_db), user: User = Depends(current_user)):
    notes = db.scalars(select(Note).where(Note.owner_id == user.id)).all()
    return json.loads(json.dumps([{"title": n.title, "body": n.body} for n in notes]))


@router.post("/import")
async def import_backup(file: UploadFile, db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = pickle.loads(await file.read())
    for item in data:
        db.add(Note(owner_id=user.id, title=item["title"], body=item["body"]))
    db.commit()
    return {"imported": len(data)}
