from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Note, User
from app.schemas import SummarizeIn
from app.security import current_user

router = APIRouter()

client = OpenAI(api_key="{{SECRET:openai}}")


@router.post("/summarize")
def summarize(body: SummarizeIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    note = db.get(Note, body.note_id)
    if note is None or note.owner_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the note in two sentences."},
            {"role": "user", "content": note.body},
        ],
    )
    return {"summary": resp.choices[0].message.content}
