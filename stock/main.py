from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
import os

engine = create_engine(
os.environ.get("DATABASE_URL", "sqlite:///stock.db")
)

class Base(DeclarativeBase):
    pass

class LigneStock(Base):
    __tablename__ = "stock"
    sku: Mapped[str] = mapped_column(primary_key=True)
    quantite: Mapped[int]

Base.metadata.create_all(engine)

app = FastAPI(title="stock")

class Quantite(BaseModel):
    quantite: int

@app.post("/stock/{sku}/ajouter")
def ajouter_stock(sku: str, q: Quantite):
    if q.quantite <= 0:
        raise HTTPException(
            status_code=422,
            detail="La quantité ajoutée doit être positive"
        )

    with Session(engine) as db:
        ligne = db.get(LigneStock, sku)

        if ligne is None:
            ligne = LigneStock(sku=sku, quantite=q.quantite)
            db.add(ligne)
        else:
            ligne.quantite += q.quantite

        db.commit()

        nouveau_stock = ligne.quantite

    return {
        "sku": sku,
        "quantite_ajoutee": q.quantite,
        "nouveau_stock": nouveau_stock
    }

@app.get("/stock/{sku}")
def lire_stock(sku: str):
    with Session(engine) as db:
        ligne = db.get(LigneStock, sku)
        if ligne is None:
            raise HTTPException(status_code=404, detail="SKU inconnu")
        return {"sku": sku, "quantite": ligne.quantite}

@app.post("/stock/{sku}/reserve")
def reserver(sku: str, q: Quantite):
    with Session(engine) as db:
        resultat = db.execute(
            update(LigneStock)
            .where(LigneStock.sku == sku, LigneStock.quantite >= q.quantite)
            .values(quantite=LigneStock.quantite - q.quantite)
        )
        db.commit()
        if resultat.rowcount == 0:
            raise HTTPException(status_code=409, detail="Stock insuffisant")
    return {"sku": sku, "reserve": q.quantite}
