from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QGroupBox
from data.db import get_connection

class LibraryWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        row = QHBoxLayout(); row.addWidget(QLabel('Pesquisar 📚'))
        self.txtSearch = QLineEdit(); self.txtSearch.setPlaceholderText('título, tags ou conteúdo')
        self.txtSearch.textChanged.connect(self.load_table)
        row.addWidget(self.txtSearch); layout.addLayout(row)
        self.table = QTableWidget(0,3); self.table.setHorizontalHeaderLabels(["ID","Título","Tags"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers); layout.addWidget(self.table)
        box = QGroupBox('Novo documento ➕'); form = QVBoxLayout()
        self.txtTitle = QLineEdit(); self.txtTitle.setPlaceholderText('Título')
        self.txtTags = QLineEdit(); self.txtTags.setPlaceholderText('tags separadas por ;')
        self.txtContent = QTextEdit(); self.txtContent.setPlaceholderText('Conteúdo')
        btnAdd = QPushButton('Salvar 📄'); btnAdd.clicked.connect(self.add_doc)
        for w in [self.txtTitle,self.txtTags,self.txtContent,btnAdd]: form.addWidget(w)
        box.setLayout(form); layout.addWidget(box)
        self.preview = QTextEdit(); self.preview.setReadOnly(True); layout.addWidget(self.preview)
        self.table.itemSelectionChanged.connect(self.on_select)
        self.load_table()
    def load_table(self):
        q=(self.txtSearch.text() or '').strip(); conn=get_connection(); cur=conn.cursor()
        if q:
            like=f"%{q}%"; cur.execute("SELECT id, title, tags FROM library_docs WHERE title LIKE ? OR tags LIKE ? OR content LIKE ? ORDER BY created_at DESC",(like,like,like))
        else:
            cur.execute("SELECT id, title, tags FROM library_docs ORDER BY created_at DESC")
        rows=cur.fetchall(); conn.close(); self.table.setRowCount(0)
        for r in rows:
            i=self.table.rowCount(); self.table.insertRow(i)
            self.table.setItem(i,0,QTableWidgetItem(str(r['id'])))
            self.table.setItem(i,1,QTableWidgetItem(r['title']))
            self.table.setItem(i,2,QTableWidgetItem(r['tags'] or ''))
    def add_doc(self):
        title=self.txtTitle.text().strip(); tags=self.txtTags.text().strip(); content=self.txtContent.toPlainText().strip()
        if not title: return
        conn=get_connection(); cur=conn.cursor()
        cur.execute("INSERT INTO library_docs(title, tags, content) VALUES (?,?,?)",(title,tags,content))
        conn.commit(); conn.close()
        self.txtTitle.clear(); self.txtTags.clear(); self.txtContent.clear()
        self.load_table()
    def on_select(self):
        items=self.table.selectedItems()
        if not items: self.preview.clear(); return
        row=items[0].row(); doc_id=int(self.table.item(row,0).text())
        conn=get_connection(); cur=conn.cursor()
        cur.execute("SELECT content FROM library_docs WHERE id=?",(doc_id,))
        r=cur.fetchone(); conn.close()
        self.preview.setPlainText(r['content'] if r else '')