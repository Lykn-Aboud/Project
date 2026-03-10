
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QMovie
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton
from modules.auth import get_current_username, authenticate_silent

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔧 Manutenção - Login")
        self.setFixedSize(400, 450)
        self.setStyleSheet("background-color: white;")

        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.setSpacing(20)
        root.setContentsMargins(0, 0, 0, 0)

        # ===== TÍTULO "Bem Vindo" =====
        title = QLabel("Bem Vindo")
        title_font = QFont()
        title_font.setPointSize(40)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("font-size: 40px; font-weight: 700;")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(title, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ===== GIF 'robot.gif' =====
        gif_label = QLabel()
        movie = QMovie("assets/robot.gif")
        movie.setScaledSize(QSize(100, 120))
        gif_label.setMovie(movie)
        gif_label.setMinimumSize(100, 120)
        gif_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        movie.start()
        root.addWidget(gif_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ===== TÍTULO "Nome" =====
        nome_lbl = QLabel("Nome")
        nome_font = QFont()
        nome_font.setPointSize(20)
        nome_font.setBold(True)
        nome_lbl.setFont(nome_font)
        nome_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        root.addWidget(nome_lbl, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ===== CAMPO DE TEXTO =====
        self.txtNome = QLineEdit()
        self.txtNome.setPlaceholderText("Digite seu nome (opcional)")
        self.txtNome.setFixedHeight(40)
        self.txtNome.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.txtNome.setObjectName("nomeInput")
        root.addWidget(self.txtNome, alignment=Qt.AlignmentFlag.AlignHCenter)

        # ===== BOTÃO ENTRAR =====
        self.btnEnter = QPushButton("Entrar")
        self.btnEnter.setFixedHeight(50)
        self.btnEnter.setObjectName("btnEntrarGrande")
        # 🔹 Fallback inline (caso QSS global falhe)
        self.btnEnter.setStyleSheet("""
            QPushButton {
                background-color: #1db954;
                color: white;
                font-size: 20px;
                font-weight: bold;
                border-radius: 10px;
                padding: 8px 18px;
            }
            QPushButton:hover {
                background-color: #12833a;
            }
        """)
        self.btnEnter.clicked.connect(self.on_enter)
        root.addWidget(self.btnEnter, alignment=Qt.AlignmentFlag.AlignHCenter)

    def on_enter(self):
        if authenticate_silent():
            nome = self.txtNome.text().strip() or (get_current_username() or "Usuário")
            self.accept(nome)

    def accept(self, nome: str):
        if hasattr(self, "on_authenticated") and callable(self.on_authenticated):
            self.on_authenticated(nome)
