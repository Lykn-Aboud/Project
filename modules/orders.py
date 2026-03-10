
# modules/orders.py
from PyQt6.QtCore import Qt, QDate, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem, QGroupBox,
    QGridLayout, QDateEdit, QMessageBox, QTreeWidget, QTreeWidgetItem, QInputDialog
)
import json
from data.db import get_connection

class OrdersWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("ordersWidget")

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        # ---------------------------------------------------------------------
        # Grupo: Dados da Ordem de Manutenção
        # 1ª linha (5 campos): Número, Tipo, Especialidade, Prioridade, Status
        # 2ª linha (3 campos): Título, Data, Responsável
        # ---------------------------------------------------------------------
        boxDados = QGroupBox("Cadastrar Nova Ordem de Manutenção")
        boxDados.setObjectName("boxDadosOM")
        gl = QGridLayout()
        gl.setHorizontalSpacing(12)
        gl.setVerticalSpacing(8)

        # ===== 1ª linha: Número (11 dígitos, auto), Tipo, Especialidade, Prioridade, Status =====
        # Número da Ordem - auto-incremento, 11 dígitos, somente leitura
        self.txtCode = QLineEdit()
        self.txtCode.setPlaceholderText("auto")
        self.txtCode.setReadOnly(True)
        self.txtCode.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.txtCode.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\d{11}$")))
        gl.addWidget(QLabel("Número da Ordem:"), 0, 0)
        gl.addWidget(self.txtCode, 0, 1)

        # Tipo
        self.cmbTipo = QComboBox()
        self.cmbTipo.addItems(["Corretiva", "Preventiva", "Preditiva", "Inspeção", "Melhoria", "Segurança"])
        gl.addWidget(QLabel("Tipo:"), 0, 2)
        gl.addWidget(self.cmbTipo, 0, 3)

        # Especialidade
        self.cmbEsp = QComboBox()
        self.cmbEsp.addItems(["Mecânica", "Elétrica", "Hidráulica", "Pneumática", "Automação"])
        gl.addWidget(QLabel("Especialidade:"), 0, 4)
        gl.addWidget(self.cmbEsp, 0, 5)

        # Prioridade
        self.cmbPrioridade = QComboBox()
        self.cmbPrioridade.addItems(["Emergencial", "Urgente", "Alta", "Média", "Baixa"])
        gl.addWidget(QLabel("Prioridade:"), 0, 6)
        gl.addWidget(self.cmbPrioridade, 0, 7)

        # Status (na 1ª linha, conforme solicitado)
        self.cmbStatus = QComboBox()
        self.cmbStatus.addItems(["Planejada", "Em Execução", "Concluída"])
        gl.addWidget(QLabel("Status:"), 0, 8)
        gl.addWidget(self.cmbStatus, 0, 9)

        # ===== 2ª linha: Título, Data, Responsável =====
        # Título
        self.txtTitle = QLineEdit()
        self.txtTitle.setPlaceholderText("Título")
        gl.addWidget(QLabel("Título:"), 1, 0)
        gl.addWidget(self.txtTitle, 1, 1, 1, 3)  # ocupa colunas 1..3 para dar respiro ao título

        # Data
        self.dateOM = QDateEdit(QDate.currentDate())
        self.dateOM.setCalendarPopup(True)
        gl.addWidget(QLabel("Data:"), 1, 4)
        gl.addWidget(self.dateOM, 1, 5)

        # Responsável
        self.txtResp = QLineEdit()
        self.txtResp.setPlaceholderText("Responsável pela OM")
        gl.addWidget(QLabel("Responsável:"), 1, 6)
        gl.addWidget(self.txtResp, 1, 7, 1, 3)  # ocupa colunas 7..9

        # ===== Equalização de espaço na 1ª linha =====
        # Tornamos as colunas de campos (1,3,5,7,9) com o mesmo stretch
        for col in (1, 3, 5, 7, 9):
            gl.setColumnStretch(col, 1)
        # E as colunas de rótulo (0,2,4,6,8) com menor stretch
        for col in (0, 2, 4, 6, 8):
            gl.setColumnStretch(col, 0)

        # ===== Equipamento (Árvore) =====
        equipBox = QGroupBox("Equipamento / Subequipamento")
        equipLayout = QVBoxLayout()
        self.treeEquip = QTreeWidget()
        self.treeEquip.setHeaderLabels(["Nome"])
        self.treeEquip.setSelectionMode(self.treeEquip.SelectionMode.SingleSelection)
        self.treeEquip.setMinimumHeight(180)
        equipBtns = QHBoxLayout()
        btnNovoEquip = QPushButton("Novo Equipamento")
        btnNovoSub = QPushButton("Novo Subequipamento")
        btnNovoEquip.clicked.connect(self._add_root_equipment)
        btnNovoSub.clicked.connect(self._add_child_equipment)
        equipBtns.addWidget(btnNovoEquip)
        equipBtns.addWidget(btnNovoSub)
        equipBtns.addStretch()
        equipLayout.addWidget(self.treeEquip)
        equipLayout.addLayout(equipBtns)
        equipBox.setLayout(equipLayout)
        gl.addWidget(equipBox, 2, 0, 1, 10)  # ocupa toda a linha

        boxDados.setLayout(gl)
        root.addWidget(boxDados)

        # ---------------------------------------------------------------------
        # Grupo: Identificação da Manutenção
        # ---------------------------------------------------------------------
        boxIdent = QGroupBox("Identificação da Manutenção")
        identLayout = QVBoxLayout()
        self.txtIdent = QTextEdit()
        self.txtIdent.setPlaceholderText("Descreva detalhamento do serviço e o motivo da OM...")
        identLayout.addWidget(self.txtIdent)
        boxIdent.setLayout(identLayout)
        root.addWidget(boxIdent)

        # ---------------------------------------------------------------------
        # Grupo: Detalhes / Observações
        # ---------------------------------------------------------------------
        boxObs = QGroupBox("Detalhes / Observações")
        obsLayout = QVBoxLayout()
        self.txtObs = QTextEdit()
        self.txtObs.setPlaceholderText("Adicione observações importantes, prazos, pendências, instruções especiais, etc.")
        obsLayout.addWidget(self.txtObs)
        boxObs.setLayout(obsLayout)
        root.addWidget(boxObs)

        # ---------------------------------------------------------------------
        # Grupo: Lista de Materiais Necessários
        # ---------------------------------------------------------------------
        boxMat = QGroupBox("Lista de Materiais Necessários")
        matLayout = QVBoxLayout()
        self.tblMat = QTableWidget(0, 6)
        self.tblMat.setHorizontalHeaderLabels(["Código", "Descrição", "Qtd", "Linha", "Máquina", "Aplicação"])
        self.tblMat.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)
        self.tblMat.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tblMat.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tblMat.horizontalHeader().setStretchLastSection(True)
        matLayout.addWidget(self.tblMat)
        btnRow = QHBoxLayout()
        self.btnAddLinha = QPushButton("Adicionar Linha"); self.btnAddLinha.setObjectName("btnAddLinha"); self.btnAddLinha.clicked.connect(self.add_row)
        self.btnRemoverLinha = QPushButton("Remover Linha"); self.btnRemoverLinha.setObjectName("btnRemoverLinha"); self.btnRemoverLinha.clicked.connect(self.remove_row)
        self.btnLimparTabela = QPushButton("Limpar Tudo"); self.btnLimparTabela.setObjectName("btnLimparTabela"); self.btnLimparTabela.clicked.connect(self.clear_rows)
        btnRow.addWidget(self.btnAddLinha); btnRow.addWidget(self.btnRemoverLinha); btnRow.addWidget(self.btnLimparTabela); btnRow.addStretch()
        matLayout.addLayout(btnRow)
        boxMat.setLayout(matLayout)
        root.addWidget(boxMat)

        # ===== Carregamentos iniciais =====
        self._load_equipment_tree()
        self._prefill_next_code_11d()

    # -------------------------------------------------------------------------
    # ÁRVORE DE EQUIPAMENTOS
    # -------------------------------------------------------------------------
    def _load_equipment_tree(self):
        self.treeEquip.clear()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, parent_id, name FROM equipments ORDER BY parent_id IS NOT NULL, id")
        rows = cur.fetchall()
        conn.close()
        items_by_id = {}
        for r in rows:
            if r["parent_id"] is None:
                item = QTreeWidgetItem([r["name"]]); item.setData(0, Qt.ItemDataRole.UserRole, r["id"])
                self.treeEquip.addTopLevelItem(item); items_by_id[r["id"]] = item
        changed = True
        while changed:
            changed = False
            for r in rows:
                pid = r["parent_id"]
                if pid is not None and r["id"] not in items_by_id and pid in items_by_id:
                    parent_item = items_by_id[pid]
                    item = QTreeWidgetItem([r["name"]]); item.setData(0, Qt.ItemDataRole.UserRole, r["id"])
                    parent_item.addChild(item); items_by_id[r["id"]] = item; changed = True
        self.treeEquip.expandAll()

    def _add_root_equipment(self):
        text, ok = QInputDialog.getText(self, "Novo Equipamento", "Nome do equipamento:")
        if not ok or not text.strip(): return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO equipments(parent_id, name) VALUES (?, ?)", (None, text.strip()))
        conn.commit(); conn.close(); self._load_equipment_tree()

    def _add_child_equipment(self):
        sel = self.treeEquip.currentItem()
        if sel is None:
            QMessageBox.warning(self, "Subequipamento", "Selecione um equipamento para adicionar um subequipamento.")
            return
        parent_id = sel.data(0, Qt.ItemDataRole.UserRole)
        text, ok = QInputDialog.getText(self, "Novo Subequipamento", "Nome do subequipamento:")
        if not ok or not text.strip(): return
        conn = get_connection(); cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO equipments(parent_id, name) VALUES (?, ?)", (parent_id, text.strip()))
        conn.commit(); conn.close(); self._load_equipment_tree()

    def _selected_equipment_path(self) -> str:
        item = self.treeEquip.currentItem()
        if item is None: return ""
        parts = []; cur = item
        while cur is not None:
            parts.append(cur.text(0)); cur = cur.parent()
        parts.reverse(); return " / ".join(parts)

    # -------------------------------------------------------------------------
    # Materiais (UI)
    # -------------------------------------------------------------------------
    def add_row(self):
        i = self.tblMat.rowCount(); self.tblMat.insertRow(i)
        for c in range(self.tblMat.columnCount()): self.tblMat.setItem(i, c, QTableWidgetItem(""))

    def remove_row(self):
        i = self.tblMat.currentRow()
        if i >= 0: self.tblMat.removeRow(i)

    def clear_rows(self):
        self.tblMat.setRowCount(0)

    def _collect_materials(self):
        mats = []
        for r in range(self.tblMat.rowCount()):
            def val(col):
                item = self.tblMat.item(r, col); return item.text().strip() if item else ""
            codigo, descricao, qtd, linha, maquina, aplicacao = val(0), val(1), val(2), val(3), val(4), val(5)
            if any([codigo, descricao, qtd, linha, maquina, aplicacao]):
                mats.append({"codigo":codigo,"descricao":descricao,"qtd":qtd,"linha":linha,"maquina":maquina,"aplicacao":aplicacao})
        return mats

    # -------------------------------------------------------------------------
    # Persistência
    # -------------------------------------------------------------------------
    def save_order(self):
        code = self.txtCode.text().strip()
        if len(code) != 11 or not code.isdigit():
            QMessageBox.warning(self, "Validação", "Falha no auto-incremento: código inválido (11 dígitos).")
            return

        title = self.txtTitle.text().strip()
        if not title:
            QMessageBox.warning(self, "Validação", "Informe o Título da OM.")
            return

        equip_path = self._selected_equipment_path()
        if not equip_path:
            QMessageBox.warning(self, "Validação", "Selecione um equipamento/subequipamento na árvore.")
            return

        prioridade = self.cmbPrioridade.currentText()
        status     = self.cmbStatus.currentText()
        meta = {
            "tipo": self.cmbTipo.currentText(),
            "especialidade": self.cmbEsp.currentText(),
            "data": self.dateOM.date().toString("yyyy-MM-dd"),
            "responsavel": self.txtResp.text().strip(),
        }

        ident = self.txtIdent.toPlainText().strip()
        obs   = self.txtObs.toPlainText().strip()
        materiais = self._collect_materials()
        desc_blob = {"identificacao": ident, "observacoes": obs, "meta": meta, "materiais": materiais}
        description = f"[UIv2]{json.dumps(desc_blob, ensure_ascii=False)}"

        conn = get_connection(); cur = conn.cursor()
        cur.execute(
            'INSERT OR REPLACE INTO orders(code, title, description, equipment, priority, status) VALUES (?,?,?,?,?,?)',
            (code, title, description, equip_path, prioridade, status)
        )
        conn.commit(); conn.close()

        QMessageBox.information(self, "Salvar", f"OM '{code}' salva com sucesso.")
        self.clear_form()
        self._prefill_next_code_11d()  # prepara o próximo código

    def _prefill_next_code_11d(self):
        self.txtCode.setText(self._next_code_11d())

    def _next_code_11d(self) -> str:
        conn = get_connection(); cur = conn.cursor()
        cur.execute('SELECT code FROM orders ORDER BY id DESC LIMIT 50')
        rows = cur.fetchall(); conn.close()
        max_n = 0
        for r in rows:
            c = r["code"] or ""
            if len(c) == 11 and c.isdigit():
                try:
                    n = int(c)
                    if n > max_n: max_n = n
                except: pass
        next_n = max_n + 1 if max_n > 0 else 1
        return f"{next_n:011d}"

    # -------------------------------------------------------------------------
    # Limpar formulário
    # -------------------------------------------------------------------------
    def clear_form(self):
        # Não limpa o número: ele será re-gerado pelo _prefill_next_code_11d após salvar.
        self.cmbTipo.setCurrentIndex(0)
        self.txtTitle.clear()
        self.cmbEsp.setCurrentIndex(0)
        self.dateOM.setDate(QDate.currentDate())
        self.cmbPrioridade.setCurrentIndex(3)  # "Média"
        self.txtResp.clear()
        self.cmbStatus.setCurrentIndex(0)      # "Planejada"
        self.txtIdent.clear()
        self.txtObs.clear()
        self.clear_rows()
