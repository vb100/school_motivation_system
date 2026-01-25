# Mokyklos motyvavimo sistema (PoC)

Serverio pusėje renderinama Django platforma vienos mokyklos taškų ir bonusų sistemai.

## Funkcionalumas (MVP)
- Vaidmenys: **ADMIN**, **TEACHER**, **STUDENT**.
- Administratorius kuria paskyras (nėra savarankiškos registracijos).
- Aktyvus semestras su biudžetais mokytojams.
- Taškai tvarkomi per **operacijų žurnalą (ledger)**.
- Mokytojas gali skirti taškus, studentas gali išpirkti bonusus.
- Top 5 reitingas pagal taškus.
- Lietuviškas UI tekstas.

## Technologijos
- Django 5.x
- Bootstrap 5
- PostgreSQL (produkcinė aplinka), SQLite (lokalus testas)
- WhiteNoise statiniams failams
- Gunicorn produkcijai

## Projekto struktūra (aukštu lygiu)
- `core/` – modeliai, paslaugų logika, vaizdai, URL.
- `templates/` – HTML šablonai (LT UI).
- `school_motivation_system/` – Django nustatymai.
- `docs/` – dokumentacija (pvz., `mvp_scope.md`).

## Lokalus paleidimas (SQLite)
> SQLite veikia be papildomų nustatymų.

### 1) Aplinkos paruošimas
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Migracijos
```bash
python manage.py makemigrations
python manage.py migrate
```

### 3) Administratoriaus sukūrimas
```bash
python manage.py createsuperuser
```

### 4) Pagrindiniai duomenys per admin
Prisijunkite prie **`/admin/`** ir sukurkite:
- **Users** su `role` reikšmėmis: `ADMIN`, `TEACHER`, `STUDENT`.
- **TeacherProfile** ir **StudentProfile** atitinkamiems vartotojams.
- **Semester** su `is_active=True`.
- **TeacherBudget** aktyviam semestrui.
- **BonusItem** su LT pavadinimu ir aprašymu.
- **SchoolSettings** įrašą mokyklos pavadinimui (naudojama skydelių antraštėje).

### 5) Paleidimas
```bash
python manage.py runserver
```

Tada atverkite:
- **`/login/`** – prisijungimas
- **`/admin/`** – administravimas

## Lokalus paleidimas (PostgreSQL per Docker)
> Jei norite Postgres lokaliai.

### 1) Paleiskite Postgres
```bash
docker-compose up -d
```

### 2) Nustatykite aplinkos kintamuosius
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
python manage.py migrate
```

## Pagrindinės puslapiai
- **`/`** – nukreipimas pagal rolę
- **`/teacher/`** – mokytojo skydelis
- **`/teacher/award/<student_id>/`** – taškų skyrimas
- **`/teacher/ranking/`** – Top 5 reitingas
- **`/student/`** – studento skydelis
- **`/student/shop/`** – bonusų parduotuvė

## Testai
```bash
python manage.py test
```

## Produkcinis diegimas (santrauka)
1) Nustatykite aplinkos kintamuosius:
```bash
export DJANGO_SECRET_KEY="..."
export DJANGO_ALLOWED_HOSTS="example.com"
export DEBUG=False
```

2) Naudokite PostgreSQL (produkcinė DB):
```bash
export DB_ENGINE=django.db.backends.postgresql
export DB_NAME=school_motivation
export DB_USER=school_user
export DB_PASSWORD=school_pass
export DB_HOST=db
export DB_PORT=5432
```

3) Surinkite statinius failus:
```bash
python manage.py collectstatic
```

4) Paleiskite su Gunicorn:
```bash
gunicorn school_motivation_system.wsgi:application
```

## Dažniausios problemos
### 1) „Too many redirects“ po login
Priežastis – vartotojui nepasirinkta `role` reikšmė. Patikrinkite admin:
- **Users → Role** turi būti nustatytas.

### 2) Postgres jungimosi klaida vietoje SQLite
Jei norite SQLite, įsitikinkite, kad **nenustatyti** DB aplinkos kintamieji:
```bash
unset DB_ENGINE DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT
```

## Architektūra
Kai tik bus pridėta architektūros schema `docs/architecture.*`, laikykite ją pirminiu šaltiniu diegimo sprendimams.
