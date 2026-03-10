from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QGroupBox
from data.db import get_connection

class MaterialsWidget(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        row = QHBoxLayout(); row.addWidget(QLabel('Buscar materiais 🔎'))
        self.txtSearch = QLineEdit(); self.txtSearch.setPlaceholderText('por código ou descrição')
        self.txtSearch.textChanged.connect(self.load_table)
        row.addWidget(self.txtSearch)
        addBtn = QPushButton('Novo material ➕'); addBtn.clicked.connect(self.add_material)
        row.addWidget(addBtn); layout.addLayout(row)
        self.table = QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(['ID','Código','Descrição','Unid.','Estoque','Estoque Mín.'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        box = QGroupBox('Mapeamento de locais 📍'); bl = QHBoxLayout()
        self.txtMatCode = QLineEdit(); self.txtMatCode.setPlaceholderText('Código material (ex.: MAT-1001)')
        self.txtLocCode = QLineEdit(); self.txtLocCode.setPlaceholderText('Código local (ex.: ALM-01)')
        self.txtQty = QLineEdit(); self.txtQty.setPlaceholderText('Quantidade (ex.: 5)')
        mapBtn = QPushButton('Mapear/Atualizar 🔁'); mapBtn.clicked.connect(self.map_location)
        for w in [self.txtMatCode,self.txtLocCode,self.txtQty,mapBtn]: bl.addWidget(w)
        box.setLayout(bl); layout.addWidget(box)
        self.locTable = QTableWidget(0,4)
        self.locTable.setHorizontalHeaderLabels(['Material','Local','Quantidade','Descrição'])
        self.locTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.locTable)
        self.load_table(); self.load_locations()
    def load_table(self):
        q=(self.txtSearch.text() or '').strip(); conn=get_connection(); cur=conn.cursor()
        if q:
            like=f"%{q}%"; cur.execute("SELECT id, code, description, unit, stock, min_stock FROM materials WHERE code LIKE ? OR description LIKE ? ORDER BY code",(like,like))
        else:
            cur.execute("SELECT id, code, description, unit, stock, min_stock FROM materials ORDER BY code")
        rows=cur.fetchall(); conn.close(); self.table.setRowCount(0)
        for r in rows:
            i=self.table.rowCount(); self.table.insertRow(i)
            for c,key in enumerate(['id','code','description','unit','stock','min_stock']):
                self.table.setItem(i,c,QTableWidgetItem(str(r[key])))
    def add_material(self):
        code=self.txtMatCode.text().strip();
        if not code: return
        conn=get_connection(); cur=conn.cursor();
        cur.execute("INSERT OR IGNORE INTO materials(code, description, unit, stock, min_stock) VALUES (?,?,?,?,?)",(code,'Novo material','UN',0,0))
        conn.commit(); conn.close(); self.load_table()
    def map_location(self):
        mcode=self.txtMatCode.text().strip(); lcode=self.txtLocCode.text().strip(); qty=self.txtQty.text().strip()
        if not (mcode and lcode and qty): return
        try: qty=float(qty)
        except: return
        conn=get_connection(); cur=conn.cursor()
        cur.execute("INSERT OR IGNORE INTO materials(code, description) VALUES (?,?)",(mcode,'Material'))
        cur.execute("INSERT OR IGNORE INTO locations(code, name) VALUES (?,?)",(lcode,'Local'))
        conn.commit()
        cur.execute("SELECT id FROM materials WHERE code=?",(mcode,)); mid=cur.fetchone()[0]
        cur.execute("SELECT id FROM locations WHERE code=?",(lcode,)); lid=cur.fetchone()[0]
        cur.execute("SELECT id FROM material_locations WHERE material_id=? AND location_id=?",(mid,lid)); row=cur.fetchone()
        if row:
            cur.execute("UPDATE material_locations SET quantity=? WHERE id=?",(qty,row[0]))
        else:
            cur.execute("INSERT INTO material_locations(material_id, location_id, quantity) VALUES (?,?,?)",(mid,lid,qty))
        conn.commit(); conn.close(); self.load_locations()
    def load_locations(self):
        conn=get_connection(); cur=conn.cursor(); cur.execute('SELECT m.code as mcode, l.code as lcode, ml.quantity as qty, m.description as mdesc FROM material_locations ml JOIN materials m ON m.id = ml.material_id JOIN locations l ON l.id = ml.location_id ORDER BY m.code, l.code')
        rows=cur.fetchall(); conn.close(); self.locTable.setRowCount(0)
        for r in rows:
            i=self.locTable.rowCount(); self.locTable.insertRow(i)
            for c,key in enumerate(['mcode','lcode','qty','mdesc']):
                self.locTable.setItem(i,c,QTableWidgetItem(str(r[key])))