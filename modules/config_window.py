
# ui/config_window.py
import os
import shutil
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton,
    QFileDialog, QHBoxLayout, QMessageBox
)

class ConfigWindow(QWidget):
    def __init__(self, app, main_window):
        super().__init__()
        self.app = app
        self.main_window = main_window
        self.setWindowTitle("⚙️ Configurações")
        self.setFixedSize(800, 600)  # Janela fixa

        # ===== Layout principal =====
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                font-family: 'Segoe UI';
                font-size: 14pt;
            }
            QLabel {
                font-weight: bold;
                color: #333333;
            }
        """)

        # ===== Configuração de Fonte =====
        lbl_font = QLabel("🔤 Fonte do Programa:")
        self.font_combo = QComboBox()
        self.font_combo.addItems(["Segoe UI", "Arial", "Calibri", "Tahoma"])
        self.font_combo.setMinimumWidth(400)
        self.font_combo.setMinimumHeight(40)

        lbl_size = QLabel("🔠 Tamanho da Fonte:")
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 48)
        self.font_size.setValue(14)
        self.font_size.setMinimumWidth(120)
        self.font_size.setMinimumHeight(40)

        layout.addWidget(lbl_font)
        layout.addWidget(self.font_combo)
        layout.addWidget(lbl_size)
        layout.addWidget(self.font_size)

        # ===== Configuração de Tema =====
        lbl_theme = QLabel("🎨 Tema:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Claro 🌞", "Escuro 🌙"])
        self.theme_combo.setMinimumWidth(400)
        self.theme_combo.setMinimumHeight(40)
        layout.addWidget(lbl_theme)
        layout.addWidget(self.theme_combo)

        # ===== Pasta de Dados =====
        lbl_folder = QLabel("📂 Pasta para armazenamento de dados:")
        self.btn_select_folder = QPushButton("📁 Selecionar Pasta")
        self.btn_select_folder.setMinimumHeight(50)
        self.btn_select_folder.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: #fff;
                font-weight: bold;
                font-size: 14pt;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #d97706; }
        """)
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.folder_path = QLabel("")
        self.folder_path.setWordWrap(True)
        layout.addWidget(lbl_folder)
        layout.addWidget(self.btn_select_folder)
        layout.addWidget(self.folder_path)

        # ===== Backup =====
        self.btn_backup = QPushButton("💾 Fazer Backup dos Dados")
        self.btn_backup.setMinimumHeight(50)
        self.btn_backup.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: #fff;
                font-weight: bold;
                font-size: 14pt;
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover { background-color: #6d28d9; }
        """)
        self.btn_backup.clicked.connect(self.do_backup)
        layout.addWidget(self.btn_backup)

        # ===== Botões de ação =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.btn_apply = QPushButton("✔ Aplicar")
        self.btn_save = QPushButton("💾 Salvar")
        self.btn_cancel = QPushButton("❌ Cancelar")

        button_style = """
            QPushButton {
                color: #ffffff;
                font-weight: bold;
                font-size: 14pt;
                border-radius: 8px;
                padding: 12px 20px;
                min-width: 180px;
                min-height: 55px;
            }
        """
        self.btn_apply.setStyleSheet(button_style + "QPushButton { background-color: #3b82f6; }")
        self.btn_save.setStyleSheet(button_style + "QPushButton { background-color: #10b981; }")
        self.btn_cancel.setStyleSheet(button_style + "QPushButton { background-color: #ef4444; }")

        self.btn_apply.clicked.connect(self.apply_changes)
        self.btn_save.clicked.connect(self.save_and_close)
        self.btn_cancel.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        # Pasta padrão
        self.default_folder = os.path.join(os.path.expanduser("~"), "Documents", "GestaoManutencao", "data")
        if not os.path.exists(self.default_folder):
            os.makedirs(self.default_folder)
        self.folder_path.setText(self.default_folder)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta")
        if folder:
            self.folder_path.setText(folder)

    def do_backup(self):
        src = self.folder_path.text()
        if not os.path.exists(src):
            QMessageBox.warning(self, "Backup", "Pasta de dados não encontrada!")
            return
        dest = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Backup")
        if dest:
            try:
                shutil.copytree(src, os.path.join(dest, "backup_data"), dirs_exist_ok=True)
                QMessageBox.information(self, "Backup", "✅ Backup realizado com sucesso!")
            except Exception as e:
                QMessageBox.critical(self, "Erro", f"Falha no backup: {e}")

    def apply_changes(self):
        # Aplicar fonte globalmente
        font_name = self.font_combo.currentText()
        font_size = self.font_size.value()
        new_font = QFont(font_name, font_size)
        self.app.setFont(new_font)  # Aplica no QApplication
        self.main_window.setFont(new_font)  # Força atualização na janela principal

        # Aplicar tema
        theme = self.theme_combo.currentText()
        if "Claro" in theme:
            self.load_qss("styles.qss")
        else:
            self.load_qss("styles_dark.qss")

        QMessageBox.information(self, "Configurações", "✨ Alterações aplicadas!")

    def save_and_close(self):
        self.apply_changes()
        self.close()

    def load_qss(self, file_name):
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            qss_path = os.path.join(os.path.dirname(base_dir), file_name)
            with open(qss_path, "r", encoding="utf-8") as f:
                self.app.setStyleSheet(f.read())
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao carregar tema: {e}")
