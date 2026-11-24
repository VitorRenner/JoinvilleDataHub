from database import CagedMovimentacao, SessionLocal

db = SessionLocal()

registro = CagedMovimentacao(
    competencia="2026-01", saldo=100, admissoes=150, demissoes=50, setor="Tecnologia"
)

db.add(registro)

db.commit()

print("Registro inserido com sucesso.")
