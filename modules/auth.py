# modules/auth.py
import os
import getpass

def get_current_username() -> str:
    """
    Retorna o usuário atual do SO de forma resiliente:
    - Tenta os.getlogin()
    - Fallback em variáveis de ambiente do Windows (USERNAME / USERDOMAIN)
    - Fallback final em getpass.getuser()
    """
    # 1) Tentativa principal
    try:
        user = os.getlogin()
        if user:
            return user
    except Exception:
        pass

    # 2) Variáveis de ambiente (boas no Windows)
    user = os.environ.get("USERNAME") or os.environ.get("USER")
    domain = os.environ.get("USERDOMAIN") or os.environ.get("DOMAIN")

    if domain and user:
        return f"{domain}\\{user}"
    if user:
        return user

    # 3) Fallback universal
    return getpass.getuser() or "usuario"

def authenticate_silent() -> bool:
    """
    Autenticação silenciosa. Para o protótipo, não valida senha – apenas retorna True.
    Em produção, você pode plugar validação adicional aqui se necessário.
    """
    return True