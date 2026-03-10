
# modules/order_view.py
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QComboBox, QDateEdit,
    QTextEdit, QPushButton, QHBoxLayout, QMessageBox, QTableWidget, QTableWidgetItem,
    QGroupBox, QTreeWidget, QTreeWidgetItem
)
import json
from data.db import get_connection


class EquipmentSelectDialog(QDialog):
    """Seleção (com criação) de Equipamento/Subequipamento via árvore."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Selecionar Equipamento")
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nome"])
        self.tree.setSelectionMode(self.tree.SelectionMode.SingleSelection)
        root.addWidget(self.tree)

        btns = QHBoxLayout()
        self.btnAddRoot = QPushButton("Novo Equipamento")
        self.btnAddChild = QPushButton("Novo Subequipamento")
        self.btnOk = QPushButton("OK")
        self.btnCancel = QPushButton("Cancelar")
        btns.addWidget(self.btnAddRoot); btns.addWidget(self.btnAddChild)
        btns.addStretch(); btns.addWidget(self.btnOk); btns.addWidget(self.btnCancel)
        root.addLayout(btns)

        self.btnAddRoot.clicked.connect(self._add_root)
        self.btnAddChild.clicked.connect(self._add_child)
        self.btnOk.clicked.connect(self.accept)
        self.btnCancel.clicked.connect(self.reject)

        self._load_tree()
        self.tree.expandAll()

    def _load_tree(self):
        self.tree.clear()
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT id, parent_id, name FROM equipments ORDER BY parent_id IS NOT NULL, id")
        rows = cur.fetchall(); conn.close()

        items = {}
        for r in rows:
            if r["parent_id"] is None:
                it = QTreeWidgetItem([r["name"]]); it.setData(0, Qt.ItemDataRole.UserRole, r["id"])
                self.tree.addTopLevelItem(it); items[r["id"]] = it

        changed = True
        while changed:
            changed = False
            for r in rows:
                pid = r["parent_id"]
                if pid is not None and r["id"] not in items and pid in items:
                    pit = items[pid]
                    it = QTreeWidgetItem([r["name"]]); it.setData(0, Qt.ItemDataRole.UserRole, r["id"])
                    pit.addChild(it); items[r["id"]] = it; changed = True

    def _add_root(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Novo Equipamento", "Nome:")
        if not ok or not name.strip():
            return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO equipments(parent_id, name) VALUES (?, ?)", (None, name.strip()))
        conn.commit(); conn.close()
        self._load_tree(); self.tree.expandAll()

    def _add_child(self):
        from PyQt6.QtWidgets import QInputDialog
        sel = self.tree.currentItem()
        if not sel:
            QMessageBox.warning(self, "Subequipamento", "Selecione um equipamento.")
            return
        pid = sel.data(0, Qt.ItemDataRole.UserRole)
        name, ok = QInputDialog.getText(self, "Novo Subequipamento", "Nome:")
        if not ok or not name.strip():
            return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO equipments(parent_id, name) VALUES (?, ?)", (pid, name.strip()))
        conn.commit(); conn.close()
        self._load_tree(); self.tree.expandAll()

    def selected_path(self) -> str:
        item = self.tree.currentItem()
        if not item:
            return ""
        parts = []; cur = item
        while cur is not None:
            parts.append(cur.text(0)); cur = cur.parent()
        parts.reverse()
        return " / ".join(parts)


class OrderViewDialog(QDialog):
    """
    Visualização/Edição de uma OM:
    - Inicia em modo leitura (Voltar, Editar).
    - Ao clicar Editar: habilita campos e materiais, aparece Salvar.
    - Alterar equipamento via árvore (com criação).
    - Salvar atualiza banco.
    - Voltar em edição pergunta se deseja cancelar alterações.
    """
    def __init__(self, order_id: int, parent=None):
        super().__init__(parent)
        self.order_id = order_id
        self.setWindowTitle("Ordem de Manutenção — Visualização")
        self.setMinimumWidth(820)
        self.editing = False

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        # Linha 1
        self.txtCode = QLineEdit(); self.txtCode.setReadOnly(True)
        grid.addWidget(QLabel("Número da Ordem:"), 0, 0); grid.addWidget(self.txtCode, 0, 1)

        self.cmbTipo = QComboBox(); self.cmbTipo.addItems(["Corretiva", "Preventiva", "Preditiva", "Inspeção", "Melhoria", "Segurança"])
        grid.addWidget(QLabel("Tipo:"), 0, 2); grid.addWidget(self.cmbTipo, 0, 3)

        self.cmbEsp = QComboBox(); self.cmbEsp.addItems(["Mecânica", "Elétrica", "Hidráulica", "Pneumática", "Automação"])
        grid.addWidget(QLabel("Especialidade:"), 0, 4); grid.addWidget(self.cmbEsp, 0, 5)

        self.cmbPrioridade = QComboBox(); self.cmbPrioridade.addItems(["Emergencial", "Urgente", "Alta", "Média", "Baixa"])
        grid.addWidget(QLabel("Prioridade:"), 1, 0); grid.addWidget(self.cmbPrioridade, 1, 1)

        self.cmbStatus = QComboBox(); self.cmbStatus.addItems(["Planejada", "Em Execução", "Concluída"])
        grid.addWidget(QLabel("Status:"), 1, 2); grid.addWidget(self.cmbStatus, 1, 3)

        self.dateOM = QDateEdit(QDate.currentDate()); self.dateOM.setCalendarPopup(True)
        grid.addWidget(QLabel("Data:"), 1, 4); grid.addWidget(self.dateOM, 1, 5)

        self.txtTitle = QLineEdit()
        grid.addWidget(QLabel("Título:"), 2, 0); grid.addWidget(self.txtTitle, 2, 1, 1, 5)

        # Equipamento
        eqBox = QHBoxLayout()
        self.txtEquip = QLineEdit(); self.txtEquip.setReadOnly(True)
        self.btnChangeEquip = QPushButton("Alterar Equipamento…")
        self.btnChangeEquip.clicked.connect(self._change_equipment)
        eqBox.addWidget(QLabel("Equipamento:")); eqBox.addWidget(self.txtEquip); eqBox.addWidget(self.btnChangeEquip)
        grid.addLayout(eqBox, 3, 0, 1, 6)

        root.addLayout(grid)

        # Textos longos
        self.txtIdent = QTextEdit(); self.txtObs = QTextEdit()
        root.addWidget(QLabel("Identificação da Manutenção"))
        root.addWidget(self.txtIdent)
        root.addWidget(QLabel("Observações"))
        root.addWidget(self.txtObs)

        # Materiais
        matBox = QGroupBox("Materiais")
        matLayout = QVBoxLayout(matBox)
        self.tblMat = QTableWidget(0, 6)
        self.tblMat.setHorizontalHeaderLabels(["Código", "Descrição", "Qtd", "Linha", "Máquina", "Aplicação"])
        self.tblMat.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # leitura por padrão
        self.tblMat.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tblMat.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tblMat.horizontalHeader().setStretchLastSection(True)
        matLayout.addWidget(self.tblMat)

        btnRow = QHBoxLayout()
        self.btnAdd = QPushButton("Adicionar Linha"); self.btnAdd.setEnabled(False); self.btnAdd.clicked.connect(self._add_row)
        self.btnDel = QPushButton("Remover Linha");  self.btnDel.setEnabled(False); self.btnDel.clicked.connect(self._del_row)
        self.btnClr = QPushButton("Limpar Tudo");    self.btnClr.setEnabled(False); self.btnClr.clicked.connect(self._clr_rows)
        btnRow.addWidget(self.btnAdd); btnRow.addWidget(self.btnDel); btnRow.addWidget(self.btnClr); btnRow.addStretch()
        matLayout.addLayout(btnRow)
        root.addWidget(matBox)

        # Barra de ações
        actions = QHBoxLayout()
        self.btnBack = QPushButton("Voltar"); self.btnBack.clicked.connect(self._on_back)
        self.btnEdit = QPushButton("Editar"); self.btnEdit.clicked.connect(self._enable_edit)
        self.btnSave = QPushButton("Salvar"); self.btnSave.clicked.connect(self._save); self.btnSave.setVisible(False)
        actions.addStretch(); actions.addWidget(self.btnBack); actions.addWidget(self.btnEdit); actions.addWidget(self.btnSave)
        root.addLayout(actions)

        # Carregar dados e iniciar em leitura
        self._load()
        self._set_readonly(True)

    # ---------- Carregar ----------
    def _load(self):
        conn = get_connection(); cur = conn.cursor()
        cur.execute("SELECT code, title, description, equipment, priority, status, created_at FROM orders WHERE id=?", (self.order_id,))
        r = cur.fetchone(); conn.close()
        if not r:
            QMessageBox.critical(self, "Erro", "Ordem não encontrada.")
            self.reject(); return

        self.txtCode.setText(r["code"] or "")
        self.txtTitle.setText(r["title"] or "")
        self.txtEquip.setText(r["equipment"] or "")
        self.cmbPrioridade.setCurrentIndex(self._index_of(self.cmbPrioridade, r["priority"]))
        self.cmbStatus.setCurrentIndex(self._index_of(self.cmbStatus, r["status"]))

        tipo = esp = data = ident = obs = ""
        mats = []
        try:
            desc = r["description"] or ""
            if desc.startswith("[UIv2]"):
                obj = json.loads(desc[len("[UIv2]"):])
                meta = obj.get("meta", {})
                tipo = meta.get("tipo", "")
                esp  = meta.get("especialidade", "")
                data = meta.get("data", "")
                ident= obj.get("identificacao", "")
                obs  = obj.get("observacoes", "")
                mats = obj.get("materiais", []) or []
        except Exception:
            pass

        self.cmbTipo.setCurrentIndex(self._index_of(self.cmbTipo, tipo))
        self.cmbEsp.setCurrentIndex(self._index_of(self.cmbEsp, esp))
        try:
            if data:
                y, m, d = map(int, data.split("-"))
                self.dateOM.setDate(QDate(y, m, d))
            else:
                self.dateOM.setDate(QDate.currentDate())
        except Exception:
            self.dateOM.setDate(QDate.currentDate())

        self.txtIdent.setPlainText(ident or "")
        self.txtObs.setPlainText(obs or "")
        self._fill_materials(mats)

    @staticmethod
    def _index_of(combo: QComboBox, value: str) -> int:
        for i in range(combo.count()):
            if combo.itemText(i).lower() == (value or "").lower():
                return i
        return 0

    # ---------- Modo leitura/edição ----------
    def _set_readonly(self, ro: bool):
        self.editing = not ro
        self.cmbTipo.setEnabled(not ro)
        self.cmbEsp.setEnabled(not ro)
        self.cmbPrioridade.setEnabled(not ro)
        self.cmbStatus.setEnabled(not ro)
        self.dateOM.setEnabled(not ro)
        self.txtTitle.setReadOnly(ro)
        self.txtIdent.setReadOnly(ro)
        self.txtObs.setReadOnly(ro)
        self.btnChangeEquip.setEnabled(not ro)
        # Materiais
        self.tblMat.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers if not ro else QTableWidget.EditTrigger.NoEditTriggers)
        self.btnAdd.setEnabled(not ro)
        self.btnDel.setEnabled(not ro)
        self.btnClr.setEnabled(not ro)

    def _enable_edit(self):
        self._set_readonly(False)
        self.btnSave.setVisible(True)

    def _on_back(self):
        if self.editing:
            resp = QMessageBox.question(
                self, "Cancelar alterações",
                "Deseja cancelar as alterações não salvas?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
        self.reject()

    # ---------- Equipamento ----------
    def _change_equipment(self):
        dlg = EquipmentSelectDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            path = dlg.selected_path()
            if path:
                self.txtEquip.setText(path)

    # ---------- Materiais ----------
    def _fill_materials(self, mats: list):
        self.tblMat.setRowCount(0)
        for m in mats:
            i = self.tblMat.rowCount()
            self.tblMat.insertRow(i)
            vals = [
                m.get("codigo", ""), m.get("descricao", ""), m.get("qtd", ""),
                m.get("linha", ""), m.get("maquina", ""), m.get("aplicacao", "")
            ]
            for c, v in enumerate(vals):
                self.tblMat.setItem(i, c, QTableWidgetItem(str(v)))

    def _collect_materials(self) -> list:
        mats = []
        for r in range(self.tblMat.rowCount()):
            def val(c):
                it = self.tblMat.item(r, c)
                return it.text().strip() if it else ""
            mats.append({
                "codigo": val(0), "descricao": val(1), "qtd": val(2),
                "linha": val(3), "maquina": val(4), "aplicacao": val(5)
            })
        # remove linhas totalmente vazias
        mats = [m for m in mats if any(m.values())]
        return mats

    def _add_row(self):
        i = self.tblMat.rowCount()
        self.tblMat.insertRow(i)
        for c in range(self.tblMat.columnCount()):
            self.tblMat.setItem(i, c, QTableWidgetItem(""))

    def _del_row(self):
        r = self.tblMat.currentRow()
        if r >= 0:
            self.tblMat.removeRow(r)

    def _clr_rows(self):
        self.tblMat.setRowCount(0)

    # ---------- Salvar ----------
    def _save(self):
        code = self.txtCode.text().strip()
        title = self.txtTitle.text().strip()
        if not title:
            QMessageBox.warning(self, "Validação", "Informe o Título.")
            return

        prioridade = self.cmbPrioridade.currentText()
        status     = self.cmbStatus.currentText()
        meta = {
            "tipo": self.cmbTipo.currentText(),
            "especialidade": self.cmbEsp.currentText(),
            "data": self.dateOM.date().toString("yyyy-MM-dd"),
        }
        ident = self.txtIdent.toPlainText().strip()
        obs   = self.txtObs.toPlainText().strip()
        mats  = self._collect_materials()
        equipment_path = self.txtEquip.text().strip()

        desc_blob = {"identificacao": ident, "observacoes": obs, "meta": meta, "materiais": mats}
        description = f"[UIv2]{json.dumps(desc_blob, ensure_ascii=False)}"

        try:
            conn = get_connection(); cur = conn.cursor()
            cur.execute(
                "UPDATE orders SET title=?, description=?, equipment=?, priority=?, status=?, updated_at=datetime('now') WHERE id=?",
                (title, description, equipment_path, prioridade, status, self.order_id)
            )
            conn.commit(); conn.close()
        except Exception as e:
            QMessageBox.critical(self, "Salvar", f"Falha ao salvar: {e}")
            return

        QMessageBox.information(self, "Salvar", f"OM {code} atualizada com sucesso.")
        self._set_readonly(True)
        self.btnSave.setVisible(False)
