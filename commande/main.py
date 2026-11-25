import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

CATALOGUE_URL = "http://localhost:8001"
STOCK_URL = "http://localhost:8002"

engine = create_engine("sqlite:///commande.db")


class Base(DeclarativeBase):
    pass


class Commande(Base):
    __tablename__ = "commandes"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str]
    quantite: Mapped[int]
    total: Mapped[float]


Base.metadata.create_all(engine)

app = FastAPI(title="commande")


class CommandeIn(BaseModel):
    sku: str
    quantite: int


@app.post("/commandes", status_code=201)
def passer_commande(c: CommandeIn):
    # 1. Le produit existe-t-il ? (on demande au Catalogue)
    rep = httpx.get(f"{CATALOGUE_URL}/produits/{c.sku}")
    if rep.status_code == 404:
        raise HTTPException(status_code=404, detail="Produit inconnu")
    produit = rep.json()

    # 2. Reste-t-il du stock ? (on demande au Stock)
    rep = httpx.post(
        f"{STOCK_URL}/stock/{c.sku}/reserve", json={"quantite": c.quantite}
    )
    if rep.status_code == 409:
        raise HTTPException(status_code=409, detail="Stock insuffisant")

    # 3. On enregistre la commande dans NOTRE base
    with Session(engine) as db:
        cmd = Commande(
            sku=c.sku, quantite=c.quantite, total=produit["prix"] * c.quantite
        )
        db.add(cmd)
        db.commit()
        db.refresh(cmd)
        return {
            "id": cmd.id,
            "sku": cmd.sku,
            "quantite": cmd.quantite,
            "total": cmd.total,
        }


@app.get("/commandes")
def lister_commandes():
    with Session(engine) as db:
        return [
            {"id": c.id, "sku": c.sku, "quantite": c.quantite, "total": c.total}
            for c in db.scalars(select(Commande))
        ]