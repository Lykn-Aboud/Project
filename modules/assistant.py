# modules/assistant.py
import re
from difflib import SequenceMatcher
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton
from data.db import get_connection

HELP = (
    "🤖 Dicas: pergunte por \"ordens abertas\", \"ordens do equipamento X\", "
    "\"materiais com baixo estoque\", ou pesquise por um tema da biblioteca "
    "técnica (ex.: 'torque hidráulico')."
)

class AssistantWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        title = QLabel("Assistente de Manutenção 🤖")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Digite sua pergunta para o assistente 🤖 ...")

        send = QPushButton("Enviar ➤")
        send.clicked.connect(self.on_ask)

        layout.addWidget(title)
        layout.addWidget(self.output)

        row = QHBoxLayout()
        row.addWidget(self.input)
        row.addWidget(send)
        layout.addLayout(row)

        self.append("Olá! Sou seu assistente. " + HELP)

    def append(self, text: str):
        self.output.append(text)

    def on_ask(self):
        q = self.input.text().strip()
        if not q:
            return
        self.append(f"👤 Você: {q}")
        ans = self.answer(q)
        self.append(f"🤖 IA: {ans}")
        self.input.clear()

    def answer(self, q: str) -> str:
        ql = q.lower()
        try:
            # ===== Intents relacionadas a Ordens =====
            if ("ordens" in ql) or ("om" in ql):
                conn = get_connection()
                cur = conn.cursor()

                if "abert" in ql:  # "aberta", "abertas"
                    cur.execute(
                        "SELECT code, title, equipment, priority "
                        "FROM orders WHERE status='Aberta' ORDER BY created_at DESC"
                    )
                elif "equip" in ql:  # "equipamento"
                    # tenta extrair o que vier após a palavra "equip"
                    m = re.search(r"equip(?:amento)?\s*([a-z0-9\- ]+)", ql)
                    like = f"%{m.group(1).strip()}%" if m else "%"
                    cur.execute(
                        "SELECT code, title, equipment, priority "
                        "FROM orders WHERE equipment LIKE ? ORDER BY created_at DESC",
                        (like,),
                    )
                elif "conclu" in ql:
                    cur.execute(
                        "SELECT code, title, equipment, priority "
                        "FROM orders WHERE status='Concluída' ORDER BY updated_at DESC"
                    )
                else:
                    # fallback: últimas 20
                    cur.execute(
                        "SELECT code, title, equipment, priority, status "
                        "FROM orders ORDER BY created_at DESC LIMIT 20"
                    )
                    rows = cur.fetchall()
                    conn.close()
                    if not rows:
                        return "Não encontrei ordens."
                    lines = [
                        f"• {r['code']}: {r['title']} ({r['equipment']}) [{r['priority']}/{r['status']}]"
                        for r in rows
                    ]
                    return "\n".join(lines)

                rows = cur.fetchall()
                conn.close()
                if not rows:
                    return "Não encontrei ordens com esse critério."
                lines = [
                    f"• {r['code']}: {r['title']} ({r['equipment']}) [{r['priority']}]"
                    for r in rows
                ]
                return "\n".join(lines)

            # ===== Intents relacionadas a Materiais =====
            if ("materiais" in ql) or ("material" in ql):
                conn = get_connection()
                cur = conn.cursor()

                if ("baixo" in ql) or ("mín" in ql):
                    # materiais abaixo do mínimo
                    cur.execute(
                        "SELECT code, description, stock, min_stock "
                        "FROM materials WHERE stock < min_stock ORDER BY code"
                    )
                    rows = cur.fetchall()
                    conn.close()
                    if not rows:
                        return "Nenhum material abaixo do mínimo. ✅"
                    lines = [
                        f"• {r['code']} - {r['description']}: {r['stock']} (min {r['min_stock']})"
                        for r in rows
                    ]
                    return "\n".join(lines)

                # tenta extrair um código do tipo MAT-1234
                m = re.search(r"\b[A-Z]{3}-\d{4}\b", q)
                if m:
                    code = m.group(0)
                    cur.execute(
                        "SELECT m.code, m.description, l.code AS loc, ml.quantity "
                        "FROM materials m "
                        "LEFT JOIN material_locations ml ON ml.material_id = m.id "
                        "LEFT JOIN locations l ON l.id = ml.location_id "
                        "WHERE m.code = ?",
                        (code,),
                    )
                    rows = cur.fetchall()
                    conn.close()
                    if not rows:
                        return "Material não encontrado."
                    header = f"{rows[0]['code']} - {rows[0]['description']}"
                    locs = [
                        f"  • Local {r['loc']}: {r['quantity']}"
                        for r in rows
                        if r["loc"] is not None
                    ]
                    return "\n".join([header] + locs if locs else [header])

            # ===== Fallback: Biblioteca (similaridade textual) =====
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT title, tags, content FROM library_docs")
            docs = cur.fetchall()
            conn.close()

            def sim(a: str, b: str) -> float:
                return SequenceMatcher(None, a, b).ratio()

            ranked = sorted(
                docs,
                key=lambda r: max(
                    sim(ql, (r["title"] or "").lower()),
                    sim(ql, (r["tags"] or "").lower()),
                    sim(ql, (r["content"] or "").lower()),
                ),
                reverse=True,
            )

            if ranked:
                top = ranked[0]
                resumo = (top["content"] or "")[:240]
                return f"Encontrei algo na biblioteca: **{top['title']}**\nResumo: {resumo}..."
            return "Não encontrei resultados. Tente reformular sua pergunta."
        except Exception as e:
            return f"Ocorreu um erro: {e}"