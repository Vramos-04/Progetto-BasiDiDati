import os
import sys
import subprocess
import socket
import signal
import platform
from dotenv import load_dotenv
from typing import Any

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

def main():
    load_dotenv()

    if is_port_in_use(PORT):
        print(f"Porta {PORT} occupata, provo a liberarla...")
        kill_process_on_port(PORT)

    if 'DB_PASSWORD' not in os.environ:
        print("ERRORE: la variabile DB_PASSWORD non è impostata nel file .env")
        sys.exit(1)

    os.environ['MYSQL_PWD'] = os.environ['DB_PASSWORD']

    run_command("python manage.py makemigrations")
    run_command("python manage.py migrate")

    os.makedirs("db_dumps", exist_ok=True)

    run_command("python manage.py dumpdata --indent 2 > db_dumps/dumpdata.json")

    # Prendi utente DB da variabile d'ambiente o imposta default
    db_user = os.environ.get('DB_USER', 'root')
    db_name = os.environ.get('DB_NAME', 'myprojectdb')

    run_command(f"mysqldump -u {db_user} {db_name} > db_dumps/backup.sql")

    print("Avvio server Django in primo piano. Premi CTRL+C per terminare.")

    try:
        run_command("python manage.py runserver")
    except KeyboardInterrupt:
        print("\nRicevuto CTRL+C, termino server Django.")
        sys.exit(0)

if __name__ == "__main__":
    main()
