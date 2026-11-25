from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, User
from app.schemas import NoteIn
from app.security import current_user

router = APIRouter()


@router.get("")
def list_notes(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.scalars(select(Note).where(Note.owner_id == user.id)).all()


@router.post("")
def create_note(body: NoteIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = Note(owner_id=user.id, title=body.title, body=body.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/by-title")
def by_title(title: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    # parametrized: safe
    rows = db.execute(
        text("SELECT id, title FROM notes WHERE owner_id = :owner AND title = :title"),
        {"owner": user.id, "title": title},
    )
    return [dict(r._mapping) for r in rows]


@router.get("/search")
def search(q: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.execute(text(f"SELECT id, title, body FROM notes WHERE owner_id = {user.id} AND title LIKE '%{q}%'"))
    return [dict(r._mapping) for r in rows]


@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="not found")
    return note
