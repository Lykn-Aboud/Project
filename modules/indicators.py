from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QGroupBox
from data.db import get_connection

class IndicatorsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0,3); self.table.setHorizontalHeaderLabels(["Indicador","Descrição","Valor"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); layout.addWidget(self.table)
        box = QGroupBox('Criar indicador dinâmico ⚙️'); form = QVBoxLayout()
        self.txtName = QLineEdit(); self.txtName.setPlaceholderText('Nome do indicador')
        self.txtDesc = QLineEdit(); self.txtDesc.setPlaceholderText('Descrição')
        self.txtSQL = QTextEdit(); self.txtSQL.setPlaceholderText('SQL que retorna um valor único (ex.: SELECT COUNT(*) FROM orders WHERE status="Aberta" )')
        btnSave = QPushButton('Salvar indicador ➕'); btnSave.clicked.connect(self.save_indicator)
        for w in [self.txtName,self.txtDesc,self.txtSQL,btnSave]: form.addWidget(w)
        box.setLayout(form); layout.addWidget(box)
        refresh = QPushButton('Atualizar indicadores 🔄'); refresh.clicked.connect(self.load_indicators); layout.addWidget(refresh)
        self.load_indicators()
    def load_indicators(self):
        conn=get_connection(); cur=conn.cursor(); cur.execute("SELECT id, name, description, sql_query FROM indicators ORDER BY created_at DESC"); rows=cur.fetchall()
        self.table.setRowCount(0)
        for r in rows:
            try:
                cur.execute(r["sql_query"]); val=cur.fetchone()[0]
            except Exception as e:
                val=f'Erro: {e}'
            i=self.table.rowCount(); self.table.insertRow(i)
            self.table.setItem(i,0,QTableWidgetItem(r["name"]))
            self.table.setItem(i,1,QTableWidgetItem(r["description"] or ""))
            self.table.setItem(i,2,QTableWidgetItem(str(val)))
        conn.close()
    def save_indicator(self):
        name=self.txtName.text().strip(); desc=self.txtDesc.text().strip(); sql=self.txtSQL.toPlainText().strip()
        if not (name and sql): return
        conn=get_connection(); cur=conn.cursor(); cur.execute("INSERT INTO indicators(name, description, sql_query) VALUES (?,?,?)",(name,desc,sql))
        conn.commit(); conn.close(); self.txtName.clear(); self.txtDesc.clear(); self.txtSQL.clear(); self.load_indicators()