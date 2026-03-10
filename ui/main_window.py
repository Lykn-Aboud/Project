
# ui/main_window.py
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QMovie, QFont
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QMessageBox, QSizePolicy, QSpacerItem
)
from modules.orders import OrdersWidget
from modules.orders_list import OrdersListWidget   # <<< NOVO: listagem
from modules.materials import MaterialsWidget
from modules.library import LibraryWidget
from modules.indicators import IndicatorsWidget
from modules.assistant import AssistantWidget
from modules.config_window import ConfigWindow  # Tela de configuração

class GifButton(QLabel):
    def __init__(self, gif_path: str, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tooltip)
        self._movie = QMovie(gif_path)
        self._movie.setScaledSize(QSize(30, 30))  # padrão 30x30
        self.setMovie(self._movie)
        self._movie.start()
    def mousePressEvent(self, ev):
        if hasattr(self, "on_clicked") and callable(self.on_clicked):
            self.on_clicked()

class MainWindow(QMainWindow):
    def __init__(self, nome: str, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Gestão de Manutenção")
        self.resize(1100, 720)

        self.root = QWidget()
        self.setCentralWidget(self.root)
        self.main = QVBoxLayout(self.root)
        self.main.setContentsMargins(18, 16, 18, 16)
        self.main.setSpacing(12)

        # ===== TOP BAR =====
        self.top = QHBoxLayout(); self.top.setContentsMargins(0, 0, 0, 0); self.top.setSpacing(10)

        # Esquerda
        self.leftTop = QHBoxLayout(); self.leftTop.setSpacing(8)
        self.btnLogout = GifButton("assets/logout.gif", "Sair"); self.btnLogout.on_clicked = self._logout; self.leftTop.addWidget(self.btnLogout)
        self.btnVoltar = GifButton("assets/voltar.gif", "Voltar"); self.btnVoltar.on_clicked = self._go_back; self.btnVoltar.setVisible(False); self.leftTop.addWidget(self.btnVoltar)

        # Centro (Bem-vindo)
        self.centerTop = QHBoxLayout()
        hello = QLabel(f"Bem-vindo(a), {nome}!")
        hfont = QFont(); hfont.setPointSize(18); hfont.setBold(True)
        hello.setFont(hfont); hello.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        self.centerTop.addWidget(hello, stretch=1)

        # Direita
        self.rightTop = QHBoxLayout(); self.rightTop.setSpacing(8)
        self.btnAtualizar = GifButton("assets/atualizar.gif", "Atualizar"); self.btnAtualizar.on_clicked = self._refresh_home; self.rightTop.addWidget(self.btnAtualizar)
        self.btnConfig    = GifButton("assets/configuração.gif", "Configuração"); self.btnConfig.on_clicked = self._open_settings; self.rightTop.addWidget(self.btnConfig)

        self._dynamicRightIcons = []  # Ícones dinâmicos (ex.: salvar/apagar na tela de cadastro)

        self.top.addLayout(self.leftTop); self.top.addLayout(self.centerTop, stretch=1); self.top.addLayout(self.rightTop)
        self.main.addLayout(self.top)

        # Centro
        self.center = QFrame(); self.center.setObjectName("centerArea")
        self.center_layout = QVBoxLayout(self.center); self.center_layout.setContentsMargins(0, 0, 0, 0); self.center_layout.setSpacing(0)
        self.main.addWidget(self.center)

        # Home
        self._home_widget = self._build_home_2col_centered()
        self._stack = []
        self._set_center(self._home_widget, is_module=False)

    def _build_home_2col_centered(self) -> QWidget:
        container = QWidget()
        outer = QVBoxLayout(container); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0); outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addItem(QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        wrap = QHBoxLayout(); wrap.setContentsMargins(0, 0, 0, 0); wrap.setSpacing(0)
        box_btn = QFrame(); box_btn.setObjectName("boxModulos")
        grid = QGridLayout(box_btn); grid.setContentsMargins(20, 18, 20, 18); grid.setHorizontalSpacing(80); grid.setVerticalSpacing(40)
        buttons = [
            ("Cadastrar ordem", "btnModuloCadastrar", self._show_cadastrar),
            ("Lista de ordens", "btnModuloListar", self._show_listar),       # <<< usa nova tela
            ("Materiais", "btnModuloMateriais", self._show_materiais),
            ("Biblioteca", "btnModuloBiblioteca", self._show_biblioteca),
            ("Indicadores", "btnModuloIndicadores", self._show_indicadores),
            ("Assistente (IA)", "btnModuloAssistente", self._show_assistente),
        ]
        positions = [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)]
        for (text, obj_name, cb), pos in zip(buttons, positions):
            btn = QPushButton(text); btn.setObjectName(obj_name); btn.setFixedHeight(58); btn.clicked.connect(cb)
            grid.addWidget(btn, *pos)
        wrap.addStretch(1); wrap.addWidget(box_btn); wrap.addStretch(1)
        outer.addLayout(wrap); outer.addItem(QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        return container

    def _set_center(self, widget: QWidget, is_module: bool):
        # Remove anterior
        if self.center_layout.count() > 0:
            old = self.center_layout.itemAt(0).widget()
            if old:
                self._stack.append(old)
        while self.center_layout.count():
            item = self.center_layout.takeAt(0); w = item.widget()
            if w: w.setParent(None)

        # Adiciona novo
        self.center_layout.addWidget(widget)
        self.btnVoltar.setVisible(is_module)

        # Ícones dinâmicos (somente para cadastro)
        if isinstance(widget, OrdersWidget):
            self._set_actions_for_cadastro(widget)
        else:
            self._clear_dynamic_actions()

    def _go_back(self):
        if not self._stack:
            self._set_center(self._home_widget, is_module=False)
            return
        prev = self._stack.pop()
        while self.center_layout.count():
            item = self.center_layout.takeAt(0); w = item.widget()
            if w: w.setParent(None)
        self.center_layout.addWidget(prev)
        self.btnVoltar.setVisible(prev is not self._home_widget)
        if isinstance(prev, OrdersWidget):
            self._set_actions_for_cadastro(prev)
        else:
            self._clear_dynamic_actions()

    def _logout(self):
        self.close()
        if hasattr(self, "on_logout") and callable(self.on_logout):
            self.on_logout()

    def _open_settings(self):
        self.config_window = ConfigWindow(self.app, self); self.config_window.show()

    def _refresh_home(self):
        self._set_center(self._home_widget, is_module=False)

    # ===== Ícones dinâmicos (Salvar/Apagar na tela de cadastro) =====
    def _clear_dynamic_actions(self):
        for w in self._dynamicRightIcons:
            self.rightTop.removeWidget(w); w.deleteLater()
        self._dynamicRightIcons.clear()

    def _set_actions_for_cadastro(self, orders_widget: OrdersWidget):
        self._clear_dynamic_actions()
        btnSave = GifButton("assets/save.gif", "Salvar OM"); btnSave.on_clicked = orders_widget.save_order
        self.rightTop.addWidget(btnSave); self._dynamicRightIcons.append(btnSave)
        btnErase = GifButton("assets/erase.gif", "Apagar / Limpar formulário"); btnErase.on_clicked = orders_widget.clear_form
        self.rightTop.addWidget(btnErase); self._dynamicRightIcons.append(btnErase)

    # ===== Navegação =====
    def _show_cadastrar(self):
        self._set_center(OrdersWidget(), is_module=True)

    def _show_listar(self):
        # Agora abre a nova tela de LISTAGEM
        self._set_center(OrdersListWidget(), is_module=True)

    def _show_materiais(self):
        self._set_center(MaterialsWidget(), is_module=True)

    def _show_biblioteca(self):
        self._set_center(LibraryWidget(), is_module=True)

    def _show_indicadores(self):
        self._set_center(IndicatorsWidget(), is_module=True)

    def _show_assistente(self):
        self._set_center(AssistantWidget(), is_module=True)
