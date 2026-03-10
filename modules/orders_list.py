
# modules/orders_list.py
from pathlib import Path
import os
import json
import csv
import datetime

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDateEdit, QPushButton, QGroupBox, QGridLayout, QTableWidget,
    QTableWidgetItem, QFileDialog, QMessageBox
)

# pandas é opcional; se não houver, cai para CSV
try:
    import pandas as pd
    HAS_PANDAS = True
except Exception:
    HAS_PANDAS = False

from data.db import get_connection
from modules.order_view import OrderViewDialog

# Arquivo de cache das larguras das colunas (na pasta do módulo)
CACHE_FILE = Path(__file__).resolve().parent / "orders_list_cache.json"


class OrdersListWidget(QWidget):
    """
    Listagem de Ordens de Manutenção:
    - Filtros superiores
    - Tabela ordenada por mais recentes (created_at DESC)
    - Multiseleção
    - Ações inferiores: Relatório (PDF) e Apagar (multi)
    - Duplo clique: abre OrderViewDialog
    - Cache de larguras das colunas
    """
    def __init__(self):
        super().__init__()
        self.setObjectName("ordersListWidget")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ===================== Filtros =====================
        boxFiltros = QGroupBox("Filtros de Busca")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.fltCode = QLineEdit(); self.fltCode.setPlaceholderText("Filtrar por ordem (11 dígitos)")
        grid.addWidget(QLabel("Ordem"), 0, 0); grid.addWidget(self.fltCode, 0, 1)

        self.fltTipo = QComboBox()
        self.fltTipo.addItems(["Todos", "Corretiva", "Preventiva", "Preditiva", "Inspeção", "Melhoria", "Segurança"])
        grid.addWidget(QLabel("Tipo"), 0, 2); grid.addWidget(self.fltTipo, 0, 3)

        self.fltDesc = QLineEdit(); self.fltDesc.setPlaceholderText("Filtrar por descrição (conteúdo)")
        grid.addWidget(QLabel("Descrição"), 0, 4); grid.addWidget(self.fltDesc, 0, 5)

        self.dateFrom = QDateEdit(); self.dateFrom.setCalendarPopup(True); self.dateFrom.setDate(QDate.currentDate().addMonths(-1))
        self.dateTo   = QDateEdit(); self.dateTo.setCalendarPopup(True); self.dateTo.setDate(QDate.currentDate())
        dateHBox = QHBoxLayout(); dateHBox.addWidget(self.dateFrom); dateHBox.addWidget(QLabel("até")); dateHBox.addWidget(self.dateTo)
        dateWrap = QWidget(); dateWrap.setLayout(dateHBox)
        grid.addWidget(QLabel("Data"), 0, 6); grid.addWidget(dateWrap, 0, 7)

        self.fltTitulo = QLineEdit(); self.fltTitulo.setPlaceholderText("Filtrar por título")
        grid.addWidget(QLabel("Título"), 1, 0); grid.addWidget(self.fltTitulo, 1, 1)

        self.fltEquip = QLineEdit(); self.fltEquip.setPlaceholderText("Filtrar por equipamento")
        grid.addWidget(QLabel("Equipamento"), 1, 2); grid.addWidget(self.fltEquip, 1, 3)

        self.fltStatus = QComboBox(); self.fltStatus.addItems(["Todos", "Planejada", "Em Execução", "Concluída"])
        grid.addWidget(QLabel("Status"), 1, 4); grid.addWidget(self.fltStatus, 1, 5)

        self.fltPend = QComboBox(); self.fltPend.addItems(["Todos", "Em aberto", "Concluída"])
        grid.addWidget(QLabel("Pendência"), 1, 6); grid.addWidget(self.fltPend, 1, 7)

        btns = QHBoxLayout()
        self.btnAplicar = QPushButton("Aplicar Filtros"); self.btnAplicar.clicked.connect(self.load_table)
        self.btnLimpar  = QPushButton("Limpar Filtros");  self.btnLimpar.clicked.connect(self.clear_filters)
        btns.addStretch(); btns.addWidget(self.btnAplicar); btns.addWidget(self.btnLimpar)
        grid.addLayout(btns, 2, 0, 1, 8)

        boxFiltros.setLayout(grid)
        root.addWidget(boxFiltros)

        # ===================== Tabela =====================
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Ordem", "Tipo", "Especialidade", "Data", "Título", "Equipamento",
            "Prioridade", "Status"
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.MultiSelection)  # multiseleção
        self.table.horizontalHeader().setStretchLastSection(True)
        # Remover “coluna auxiliar” com numeração:
        self.table.verticalHeader().setVisible(False)

        # Salvar cache de larguras automaticamente ao redimensionar
        self.table.horizontalHeader().sectionResized.connect(self._save_column_widths)

        root.addWidget(self.table)

        # Duplo clique → visualizar/editar
        self.table.itemDoubleClicked.connect(self._open_view_dialog)

        # ===================== Ações inferior =====================
        actions = QHBoxLayout()
        self.btnRelatorio = QPushButton("Relatório")  # <--- renomeado
        self.btnRelatorio.clicked.connect(self.report_selected_multi)
        self.btnApagar    = QPushButton("Apagar")
        self.btnApagar.clicked.connect(self.delete_selected_multi)
        actions.addWidget(self.btnRelatorio)
        actions.addWidget(self.btnApagar)
        actions.addStretch()
        root.addLayout(actions)

        # Inicial
        self.load_table()
        self._restore_column_widths(default_title_width=320)

    # ---------- Cache de larguras ----------
    def _save_column_widths(self, *_args):
        widths = [self.table.columnWidth(i) for i in range(self.table.columnCount())]
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(widths, f)
        except Exception:
            pass

    def _restore_column_widths(self, default_title_width: int = 320):
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    widths = json.load(f)
                for i, w in enumerate(widths):
                    self.table.setColumnWidth(i, int(w))
            else:
                # Título mais largo por padrão
                self.table.setColumnWidth(4, default_title_width)
        except Exception:
            self.table.setColumnWidth(4, default_title_width)

    # ---------- Filtros ----------
    def clear_filters(self):
        self.fltCode.clear()
        self.fltTipo.setCurrentIndex(0)
        self.fltDesc.clear()
        self.dateFrom.setDate(QDate.currentDate().addMonths(-1))
        self.dateTo.setDate(QDate.currentDate())
        self.fltTitulo.clear()
        self.fltEquip.clear()
        self.fltStatus.setCurrentIndex(0)
        self.fltPend.setCurrentIndex(0)
        self.load_table()

    # ---------- Carregar tabela ----------
    def load_table(self):
        sql = "SELECT id, code, title, description, equipment, priority, status, created_at FROM orders WHERE 1=1"
        params = []

        # Filtros
        code = self.fltCode.text().strip()
        if code:
            sql += " AND code LIKE ?"; params.append(f"%{code}%")

        tipo = self.fltTipo.currentText()
        if tipo != "Todos":
            # 'tipo' está em description JSON => filtramos por texto
            sql += " AND description LIKE ?"; params.append(f"%\"tipo\": \"{tipo}\"%")

        desc = self.fltDesc.text().strip()
        if desc:
            sql += " AND description LIKE ?"; params.append(f"%{desc}%")

        d1 = self.dateFrom.date().toString("yyyy-MM-dd")
        d2 = self.dateTo.date().toString("yyyy-MM-dd")
        if d1:
            sql += " AND date(created_at) >= date(?)"; params.append(d1)
        if d2:
            sql += " AND date(created_at) <= date(?)"; params.append(d2)

        titulo = self.fltTitulo.text().strip()
        if titulo:
            sql += " AND title LIKE ?"; params.append(f"%{titulo}%")

        equip = self.fltEquip.text().strip()
        if equip:
            sql += " AND equipment LIKE ?"; params.append(f"%{equip}%")

        status = self.fltStatus.currentText()
        if status != "Todos":
            sql += " AND status = ?"; params.append(status)

        pend = self.fltPend.currentText()
        if pend == "Em aberto":
            sql += " AND status IN ('Planejada','Em Execução')"
        elif pend == "Concluída":
            sql += " AND status = 'Concluída'"

        # Mais recente → mais antiga
        sql += " ORDER BY datetime(created_at) DESC"

        conn = get_connection(); cur = conn.cursor()
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
        conn.close()

        # Preencher
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            values = [
                r["code"] or "",
                self._meta_value(r["description"], "tipo"),
                self._meta_value(r["description"], "especialidade"),
                (self._meta_value(r["description"], "data") or r["created_at"] or "")[:10],
                r["title"] or "",
                r["equipment"] or "",
                r["priority"] or "",
                r["status"] or "",
            ]
            for c, val in enumerate(values):
                self.table.setItem(i, c, QTableWidgetItem(str(val)))

    @staticmethod
    def _meta_value(description: str, key: str) -> str:
        if not description:
            return ""
        try:
            if description.startswith("[UIv2]"):
                payload = description[len("[UIv2]"):]
                obj = json.loads(payload)
                meta = obj.get("meta", {})
                return meta.get(key, "") or ""
        except Exception:
            pass
        return ""

    # ---------- Duplo clique ----------
    def _open_view_dialog(self, item: QTableWidgetItem):
        row = item.row()
        code_item = self.table.item(row, 0)
        if not code_item:
            return
        code = code_item.text().strip()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id FROM orders WHERE code=?", (code,))
        r = cur.fetchone()
        conn.close()
        if not r:
            QMessageBox.warning(self, "Visualização", "Ordem não encontrada.")
            return
        dlg = OrderViewDialog(r["id"], self)
        dlg.exec()
        self.load_table()

    # ---------- Relatório (multi) ----------
    def report_selected_multi(self):
        ids = self._selected_order_ids()
        if not ids:
            QMessageBox.warning(self, "Relatório", "Selecione uma ou mais ordens na tabela.")
            return
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta para salvar PDFs")
        if not folder:
            return
        ok_count, err_msgs = 0, []
        for oid in ids:
            try:
                self._generate_pdf_for_order(oid, folder)
                ok_count += 1
            except Exception as e:
                err_msgs.append(f"ID {oid}: {e}")
        if err_msgs:
            QMessageBox.warning(self, "Relatório", f"Gerados {ok_count} PDFs. Erros:\n" + "\n".join(err_msgs))
        else:
            QMessageBox.information(self, "Relatório", f"Gerados {ok_count} PDFs na pasta:\n{folder}")

    def _generate_pdf_for_order(self, order_id: int, folder: str):
        """
        Gera um PDF COMPLETO da ordem:
          - Cabeçalho com campos principais
          - Identificação e Observações (com quebras de linha)
          - Responsável (se existir em meta)
          - Tabela de Materiais
        Salva como OM_<code>.pdf na pasta fornecida.
        """
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT code, title, description, equipment, priority, status, created_at FROM orders WHERE id=?", (order_id,))
        r = cur.fetchone(); conn.close()
        if not r:
            raise RuntimeError("Ordem não encontrada.")

        code = r["code"]; title = r["title"]; equip = r["equipment"]; prio = r["priority"]; status = r["status"]
        created = r["created_at"] or ""
        tipo = esp = data = ident = obs = responsavel = ""
        materiais = []

        try:
            if r["description"] and r["description"].startswith("[UIv2]"):
                obj = json.loads(r["description"][len("[UIv2]"):])
                meta = obj.get("meta", {}) or {}
                tipo = meta.get("tipo", "") or ""
                esp  = meta.get("especialidade", "") or ""
                data = meta.get("data", "") or ""
                responsavel = meta.get("responsavel", "") or ""
                ident = obj.get("identificacao", "") or ""
                obs   = obj.get("observacoes", "") or ""
                materiais = obj.get("materiais", []) or []
        except Exception:
            pass

        data_text = data or (created[:10] if created else "")
        ident_html = ident.replace("\n", "<br/>")
        obs_html   = obs.replace("\n", "<br/>")

        # Monta tabela de materiais (HTML)
        def _mat_table_html(mats: list) -> str:
            if not mats:
                return "<em>Sem materiais informados.</em>"
            rows = []
            rows.append("<table border='1' cellspacing='0' cellpadding='4' style='border-collapse:collapse; font-size:10pt;'>")
            rows.append("<tr style='background:#f2f2f2; font-weight:bold;'><td>Código</td><td>Descrição</td><td>Qtd</td><td>Linha</td><td>Máquina</td><td>Aplicação</td></tr>")
            for m in mats:
                rows.append(
                    "<tr>"
                    f"<td>{(m.get('codigo',''))}</td>"
                    f"<td>{(m.get('descricao',''))}</td>"
                    f"<td>{(m.get('qtd',''))}</td>"
                    f"<td>{(m.get('linha',''))}</td>"
                    f"<td>{(m.get('maquina',''))}</td>"
                    f"<td>{(m.get('aplicacao',''))}</td>"
                    "</tr>"
                )
            rows.append("</table>")
            return "\n".join(rows)

        mats_html = _mat_table_html(materiais)

        html = f"""
        <html><head><meta charset="utf-8">
        <style>
            body {{ font-family: Segoe UI, Arial, sans-serif; font-size: 11pt; }}
            h1   {{ font-size: 16pt; margin-bottom: 6px; }}
            .row {{ margin: 2px 0; }}
            .label {{ font-weight: bold; }}
            .box {{ margin-top: 10px; }}
        </style>
        </head><body>
            <h1>Ordem {code}</h1>
            <div class="row"><span class="label">Título:</span> {title}</div>
            <div class="row"><span class="label">Tipo:</span> {tipo} &nbsp;&nbsp; <span class="label">Especialidade:</span> {esp}</div>
            <div class="row"><span class="label">Prioridade:</span> {prio} &nbsp;&nbsp; <span class="label">Status:</span> {status}</div>
            <div class="row"><span class="label">Data:</span> {data_text} &nbsp;&nbsp; <span class="label">Equipamento:</span> {equip}</div>
            <div class="row"><span class="label">Responsável:</span> {responsavel}</div>

            <div class="box">
                <div class="label">Identificação:</div>
                <div>{ident_html}</div>
            </div>

            <div class="box">
                <div class="label">Observações:</div>
                <div>{obs_html}</div>
            </div>

            <div class="box">
                <div class="label">Materiais:</div>
                {mats_html}
            </div>

            <div class="row" style="margin-top:20px;color:#666;">
                Gerado em {datetime.datetime.now():%Y-%m-%d %H:%M}
            </div>
        </body></html>
        """

        filename = os.path.join(folder, f"OM_{code}.pdf")
        printer = QPrinter()
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(filename)

        doc = QTextDocument(); doc.setHtml(html); doc.print(printer)

    # ---------- Apagar (multi) ----------
    def delete_selected_multi(self):
        ids = self._selected_order_ids()
        if not ids:
            QMessageBox.warning(self, "Apagar", "Selecione uma ou mais ordens na tabela.")
            return
        resp = QMessageBox.question(self, "Apagar", f"Apagar {len(ids)} ordem(ns)?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No)
        if resp != QMessageBox.StandardButton.Yes:
            return
        try:
            conn = get_connection(); cur = conn.cursor()
            qmarks = ",".join("?" for _ in ids)
            cur.execute(f"DELETE FROM orders WHERE id IN ({qmarks})", tuple(ids))
            conn.commit(); conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Apagar", f"Falha ao apagar: {e}")
            return
        self.load_table()

    # ---------- Seleção ----------
    def _selected_order_ids(self):
        rows = {item.row() for item in self.table.selectedItems()}
        codes = []
        for r in rows:
            item = self.table.item(r, 0)
            if item:
                codes.append(item.text())
        if not codes:
            return []
        conn = get_connection(); cur = conn.cursor()
        qmarks = ",".join("?" for _ in codes)
        cur.execute(f"SELECT id FROM orders WHERE code IN ({qmarks})", tuple(codes))
        found = cur.fetchall(); conn.close()
        return [f["id"] for f in found]
