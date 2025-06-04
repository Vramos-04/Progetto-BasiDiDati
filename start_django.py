import os
import sys
import subprocess
import socket
from dotenv import load_dotenv
import signal

PORT = 8000

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    try:
        result = subprocess.run(
            ['lsof', '-ti', f'tcp:{port}'],
            capture_output=True,
            text=True
        )
        pids = result.stdout.strip().split('\n')
        for pid in pids:
            if pid:
                print(f'Uccido processo {pid} sulla porta {port}')
                os.kill(int(pid), signal.SIGKILL)
    except Exception as e:
        print(f"Errore tentando di killare processo: {e}")

def run_command(command):
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

    # Controlla che DB_PASSWORD e DB_USER siano settate nell'env
    if 'DB_PASSWORD' not in os.environ:
        print("ERRORE: la variabile DB_PASSWORD non è impostata nel file .env")
        sys.exit(1)
    if 'DB_USER' not in os.environ:
        print("ERRORE: la variabile DB_USER non è impostata nel file .env")
        sys.exit(1)

    db_user = os.environ['DB_USER']
    os.environ['MYSQL_PWD'] = os.environ['DB_PASSWORD']

    run_command("python manage.py makemigrations")
    run_command("python manage.py migrate")

    os.makedirs("db_dumps", exist_ok=True)

    run_command("python manage.py dumpdata --indent 2 > db_dumps/dumpdata.json")
    # Qui usa db_user dinamicamente
    run_command(f"mysqldump -u {db_user} myprojectdb > db_dumps/backup.sql")

    print("Avvio server Django in primo piano. Premi CTRL+C per terminare.")

    try:
        run_command("python manage.py runserver")
    except KeyboardInterrupt:
        print("\nRicevuto CTRL+C, termino server Django.")
        sys.exit(0)

if __name__ == "__main__":
    main()
