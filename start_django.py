import os
import sys
import subprocess
import socket
import signal
import platform
from dotenv import load_dotenv
from typing import Any
import shutil
import atexit

PORT = 8000

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port: Any) -> None:
    system = platform.system()

    if system == "Windows":
        _kill_process_on_port_windows(port)
    else:
        _kill_process_on_port_unix(port)

def _kill_process_on_port_windows(port: Any) -> None:
    try:
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            shell=True
        )
        pids = [
            line.split()[-1]
            for line in result.stdout.splitlines()
            if f":{port} " in line and "LISTENING" in line
        ]
        for pid in pids:
            if pid:
                print(f'Uccido processo {pid} sulla porta {port}')
                subprocess.run(['taskkill', '/PID', pid, '/F'], shell=True)
    except Exception as e:
        print(f"Errore tentando di killare processo su Windows: {e}")

def _kill_process_on_port_unix(port: Any) -> None:
    try:
        result = subprocess.run(
            ['lsof', '-ti', f'tcp:{port}'],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        for pid in filter(None, pids):
            print(f'Uccido processo {pid} sulla porta {port}')
            os.kill(int(pid), signal.SIGKILL)
    except Exception as e:
        print(f"Errore tentando di killare processo su Unix: {e}")

def run_command(command: str) -> None:
    print(f"Eseguo: {command}")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Errore nel comando: {command}")
        sys.exit(1)

def dump_database(db_user: str, db_name: str) -> None:
    print("Creo il dump aggiornato del database MySQL...")
    mysqldump_path = shutil.which("mysqldump")
    if not mysqldump_path:
        print("Errore: 'mysqldump' non trovato nel PATH.")
        return
    os.makedirs("db_dumps", exist_ok=True)
    with open("db_dumps/backup.sql", "w") as outfile:
        subprocess.run(
            [mysqldump_path, "-u", db_user, db_name],
            stdout=outfile,
            check=True
        )
    print("Dump aggiornato salvato in db_dumps/backup.sql")

def main():
    load_dotenv()

    if is_port_in_use(PORT):
        print(f"Porta {PORT} occupata, provo a liberarla...")
        kill_process_on_port(PORT)

    if 'DB_PASSWORD' not in os.environ:
        print("ERRORE: la variabile DB_PASSWORD non è impostata nel file .env")
        sys.exit(1)

    os.environ['MYSQL_PWD'] = os.environ['DB_PASSWORD']

    db_user = os.environ.get('DB_USER', 'root')
    db_name = os.environ.get('DB_NAME', 'myprojectdb')

    # Registro il dump da eseguire alla chiusura
    atexit.register(dump_database, db_user, db_name)

    # Opzionale: ripristina DB da dump all'avvio
    restore_db = input("Vuoi ripristinare il database dal dump SQL prima di generare i models? (y/n): ").lower()
    if restore_db == 'y':
        dump_path = 'db_dumps/backup.sql'
        if not os.path.exists(dump_path):
            print(f"ERRORE: Il file {dump_path} non esiste.")
            sys.exit(1)
        run_command(f'mysql -u {db_user} {db_name} < {dump_path}')
        print("Database ripristinato con successo dal dump SQL.")

    app_name = 'myapp' 
    models_path = os.path.join(app_name, 'models.py')
    print(f"Genero automaticamente {models_path} dalle tabelle del database MySQL...")

    run_command(f"python manage.py inspectdb > {models_path}")

    run_command("python manage.py makemigrations")
    run_command("python manage.py migrate")

    run_command("python manage.py dumpdata --indent 2 > db_dumps/dumpdata.json")

    print("Avvio server Django in primo piano. Premi CTRL+C per terminare.")

    try:
        run_command("python manage.py runserver")
    except KeyboardInterrupt:
        print("\nRicevuto CTRL+C, termino server Django.")
        sys.exit(0)

if __name__ == "__main__":
    main()
