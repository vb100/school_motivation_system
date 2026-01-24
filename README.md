# Mokyklos motyvavimo sistema (PoC)

Server-rendered Django platforma mokyklos taškų ir bonusų sistemai.

## Technologijos
- Django 5.x
- Bootstrap 5
- PostgreSQL (produkcinė aplinka), SQLite (lokalus testas)
- WhiteNoise statiniams failams
- Gunicorn produkcijai

## Lokalus paleidimas

### 1) Aplinkos paruošimas
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Duomenų bazė
Numatytasis variantas naudoja SQLite ir veikia be papildomų nustatymų.

Jei norite PostgreSQL (rekomenduojama), paleiskite:
```bash
docker-compose up -d
```

Nustatykite aplinkos kintamuosius:
```bash
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=school_motivation
export DB_USER=school_user
export DB_PASSWORD=school_pass
export DB_HOST=localhost
export DB_PORT=5432
```

### 3) Migracijos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 4) Administratoriaus sukūrimas
```bash
python manage.py createsuperuser
```

### 5) Pagrindiniai duomenys
- Prisijunkite prie `/admin/`.
- Sukurkite vartotojus ir pasirinkite `role` (ADMIN, TEACHER, STUDENT).
- Sukurkite `TeacherProfile` ir `StudentProfile` atitinkamiems vartotojams.
- Sukurkite `Semester` ir pažymėkite `is_active`.
- Sukurkite `TeacherBudget` aktyviam semestrui.
- Sukurkite `BonusItem` (LT pavadinimai/aprašymai).

### 6) Paleidimas
```bash
python manage.py runserver
```

## Testai
```bash
python manage.py test
```

## Produkcinis diegimas (santrauka)
- Nustatykite `DJANGO_SECRET_KEY` ir `DJANGO_ALLOWED_HOSTS`.
- Naudokite PostgreSQL.
- Surinkite statinius failus:
```bash
python manage.py collectstatic
```
- Paleiskite su Gunicorn:
```bash
gunicorn school_motivation_system.wsgi:application
```

## Pastabos apie architektūrą
Kai tik bus pridėta architektūros schema `docs/architecture.*`, laikykite ją pirminiu šaltiniu diegimo sprendimams.
