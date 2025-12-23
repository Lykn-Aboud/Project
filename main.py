
# main.py
import sys
import os
from PyQt6.QtWidgets import QApplication
from ui.login import LoginWindow
from ui.main_window import MainWindow
from data.db import init_db

def load_styles(app):
    app.setStyle("Fusion")  # Força estilo consistente
    base_dir = os.path.dirname(os.path.abspath(__file__))
    qss_path = os.path.join(base_dir, "styles.qss")
    try:
        with open(qss_path, "r", encoding="utf-8") as f:
            css = f.read()
            app.setStyleSheet(css)
            print(f"[Styles] Carregado: {qss_path} ({len(css)} chars)")
    except Exception as e:
        print(f"[Styles] Falha ao carregar '{qss_path}': {e}")

def run():
    init_db()
    app = QApplication(sys.argv)
    load_styles(app)

    login = LoginWindow()

    def show_login():
        nonlocal login
        login = LoginWindow()
        login.on_authenticated = on_auth
        login.show()

    def on_auth(nome):
        w = MainWindow(nome, app)
        app.main_window = w
        w.on_logout = show_login
        w.show()
        login.close()

    login.on_authenticated = on_auth
    login.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    run()

