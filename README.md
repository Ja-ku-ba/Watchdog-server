# Watchdog
## Serwer, w systemie do zarządzania monitoringem z detekcją twarzy, oparte o urządzenie monitorujące na RaspbberyPi 5

Aplikacja składa się z 3 modułów
- https://github.com/Ja-ku-ba/Watchdog-server
- https://github.com/Ja-ku-ba/Watchdog-mobile-app
- https://github.com/Ja-ku-ba/Watchdog-Raspberrypi

Wymagane:
- Linux na serwerze. Konfiguracja bazuje na Ubuntu
- Konto w Firebase i dostęp do Firebase Cloud Messaging
- Domena
- Python 3.12

1. Instrukcja konfiguracji serwera znajduje się w server_config/server_readme
2. Instrukcja konfiguracji pythona w projekcie znajduje się w server_config/python_readme
Aby uruchomić projek na serwerze musisz:
```bash
pip install virtualenv

```

Pobierz projekt
```bash
```

Utwórz środowisko wirtualne i zainstaluj zależności
```bash
python -m virtualenv .venv
source .venv/bin/activate
```

Zainstaluj zależności
## Konfiguracja serwera

Utwórz użytkonika w systemie z dostępem do projektu
```bash
sudo useradd -m watchdog_user
sudo passwd watchdog_user
```

Pobierz projekt
```bash
cd var/www/
git clone https://github.com/Ja-ku-ba/Watchdog-server
```

Nadaj użytkonikowi uprawnieni do folderu
```bash
sudo chown -R watchdog_user:watchdog_user /var/www/Watchdog-server
su - watchdog_user
```

Skopiuj plik env do .env
```bash
cp env .env
```

Zainstaluj zależności pythonowe
```bash
cd Watchdog-server
python -m virtualenv .venv
source .venv/bin/activate
pip install -r server_config/requirements.txt
```

Skonfiguruj UFW
```bash
sudo ufw enable
sudo ufw allow OpenSSH
sudo ufw allow 80
sudo ufw allow 443
```

Zainstaluj i skonfiguruj fail2ban
```bash
sudo apt install fail2ban
sudo systemctl start fail2ban
sudo systemctl enable fail2ban
```

Konfigurację fail2ban, muszisz przeprowadzić samodzielnie
Edytuj plik
```bash
sudo nano /etc/fail2ban/jail.local
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```
Dokumentację do konfiguracji znajdziesz na stronie:
- https://github.com/fail2ban/fail2ban/blob/master/config/jail.conf

Odśwież fail2ban
```bash
sudo systemctl restart fail2ban
```

Konnfiguracja postgresql
```
sudo apt install postgresql postgresql-contrib
sudo -i -u postgres
sudo -u postgres psql
```

Dodaj bazę danych w postgresie
```bash
CREATE USER watchdog_db_user WITH PASSWORD 'TOWJE_SILNE_WYGENEROWANE_HASLO';
CREATE DATABASE app_db
  WITH
  OWNER = watchdog_db_user
  ENCODING = 'UTF8';

\q

sudo systemctl restart postgresql
```

Skonfiguruj dane dostępowe do bazy danych w pliku
```bash
cd /var/www/Watchdog-server/
nano .env
```

Skonfiguruj FIREBASE CLOUD MESSAGING, do powiadomień
utwórz folder w jakim bedzie się znajdować plik
```bash
cd /var/www/Watchdog-server
mkdir config
cd config
```

Uruchom kampanie w FIREBASE CLOUD MESSAGING
W obecnym katalogu config skopiuj i przekelej klucz z FIREBASE CLOUD MESSAGING
Ustaw ścieżkę do klucza w pliku .env

Pobierz firebase cli
```
pip install firebase-admin
export GOOGLE_APPLICATION_CREDENTIALS=/etc/firebase/service-account.json
```

Zrób migracje do bazy danych
```bash
cd /var/www/Watchdog-serwer
alembic revision --autogenerate -m "initial-db-migration"
```

Utwórz serwis odpowiedzialny za startowanie aplikacji po uruchomieniu
```bash
cd /etc/systemd/system
nano watchdog-api.service
```
Do tego pliku przkopiuj zawartość server_config/watchdog-api.service, dostosowując swojego użytkownika


Skonfiguruj nginx
```bash
sudo apt install nginx
cd /etc/nginx/sites-available/
nano watchdog-api
```

Minimalan konfiguracja serwera
```bash
server {
    listen 80;
    listen [::]:80;
    server_name twoja-domena.pl www.twoja-domena.pl;

    location / {
        proxy_pass http://localhost:8000;  # lub inny port na jakim uruchomisz serwer
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }


    location ~ /\. {
        deny all;
        return 404;
    }

    location ~* \.(env|git|svn|htaccess)$ {
        deny all;
        return 404;
    }
}
```

Utwórz symlink
```bash
sudo ln -s /etc/nginx/sites-available/watchdog-api /etc/nginx/sites-enabled/
```

Przeładuj nginx
```bash
sudo systemctl reload nginx
```

Uruchom certbota
```bash
sudo certbot --nginx -d twoja-domena.pl -d www.twoja-domena.pl
```

Uruchom od nowa serwer
```bash
sudo reboot
```