import os
import sys
import subprocess
import socket
import signal
import platform
from dotenv import load_dotenv

PORT = 8000

def log(msg):
    print(f"[INFO] {msg}")

def err(msg):
    print(f"[ERRORE] {msg}", file=sys.stderr)

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    try:
        if platform.system() == "Windows":
            # Windows: usa netstat + taskkill
            result = subprocess.run(
                ['netstat', '-ano'],
                capture_output=True,
                text=True,
                shell=True
            )
            lines = result.stdout.splitlines()
            pids = []
            for line in lines:
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    pids.append(pid)
            for pid in pids:
                log(f'Uccido processo {pid} sulla porta {port}')
                subprocess.run(['taskkill', '/PID', pid, '/F'], shell=True)
        else:
            # Mac/Linux
            result = subprocess.run(
                ['lsof', '-ti', f'tcp:{port}'],
                capture_output=True,
                text=True
            )
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    log(f'Uccido processo {pid} sulla porta {port}')
                    os.kill(int(pid), signal.SIGKILL)
    except Exception as e:
        err(f"Errore tentando di killare processo: {e}")

def check_command_exists(command):
    """Verifica se un comando è disponibile nel PATH."""
    from shutil import which
    return which(command) is not None

def run_command(command):
    log(f"Eseguo: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError:
        err(f"Errore nel comando: {command}")
        sys.exit(1)

def main():
    load_dotenv()

    if is_port_in_use(PORT):
        log(f"Porta {PORT} occupata, provo a liberarla...")
        kill_process_on_port(PORT)

    if 'DB_PASSWORD' not in os.environ:
        err("La variabile DB_PASSWORD non è impostata nel file .env")
        sys.exit(1)

    os.environ['MYSQL_PWD'] = os.environ['DB_PASSWORD']

    # Controlla che mysqldump esista
    if not check_command_exists("mysqldump"):
        err("mysqldump non trovato. Assicurati che MySQL sia installato e mysqldump sia nel PATH.")
        sys.exit(1)

    # Esegui migrazioni
    run_command("python manage.py makemigrations")
    run_command("python manage.py migrate")

    os.makedirs("db_dumps", exist_ok=True)

    # Dump dati Django
    run_command("python manage.py dumpdata --indent 2 > db_dumps/dumpdata.json")

    # Prendi nome utente e db da env o metti default
    db_user = os.environ.get("DB_USER", "root")
    db_name = os.environ.get("DB_NAME", "myprojectdb")

    run_command(f"mysqldump -u {db_user} {db_name} > db_dumps/backup.sql")

    log("Avvio server Django in primo piano. Premi CTRL+C per terminare.")

    try:
        run_command("python manage.py runserver")
    except KeyboardInterrupt:
        log("Ricevuto CTRL+C, termino server Django.")
        sys.exit(0)

if __name__ == "__main__":
    main()
