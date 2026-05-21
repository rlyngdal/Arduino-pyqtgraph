# Opsætning – Udgiftsrefusionsapp

## Hurtig start (lokal test)

```bash
cd expense-app
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # Rediger .env med dine egne værdier
uvicorn app.main:app --reload
```
Åbn http://localhost:8000

---

## 1. Opret Google OAuth (gratis)

1. Gå til https://console.cloud.google.com → "APIs & Services" → "Credentials"
2. Opret projekt (f.eks. "Fritidsklub")
3. Klik "Create Credentials" → "OAuth 2.0 Client ID"
4. Vælg **Web application**
5. Under "Authorized redirect URIs" tilføj:
   - `http://localhost:8000/auth/google/callback` (til test)
   - `https://DIN-APP-URL/auth/google/callback` (til produktion)
6. Kopiér **Client ID** og **Client Secret** ind i `.env`

---

## 2. Opret Microsoft OAuth (valgfrit)

1. Gå til https://portal.azure.com → "App registrations" → "New registration"
2. Navn: "Fritidsklub", Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
3. Redirect URI: `https://DIN-APP-URL/auth/microsoft/callback`
4. Gå til "Certificates & secrets" → "New client secret"
5. Kopiér **Application (client) ID** og secret-værdien ind i `.env`

---

## 3. Deploy gratis på Railway

1. Opret konto på https://railway.app
2. "New Project" → "Deploy from GitHub repo"
3. Vælg dette repository
4. Sæt **Root Directory** til `expense-app`
5. Tilføj miljøvariabler (fra `.env`) under "Variables"
6. Railway giver dig en URL, f.eks. `https://fritidsklub.up.railway.app`
7. Opdatér `APP_URL` i miljøvariablerne til denne URL
8. Opdatér OAuth redirect URIs med den nye URL

**Start-kommando** (Railway sætter automatisk PORT):
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 4. Konfigurér admin-adgang

I `.env` skal du liste kasserernes e-mails:
```
ADMIN_EMAILS=din@email.dk,anden_kasserer@email.dk
```

Den første gang en person logger ind med en af disse e-mails, får de automatisk admin-adgang.

---

## Sikkerhedsoverblik

- Alle filer ligger på serveren og kan kun downloades af admin eller ejeren af udgiften
- Login sker udelukkende via Google/Microsoft – ingen adgangskoder gemmes
- Sessions krypteres med `SECRET_KEY`
- Filtyper valideres (kun PDF, JPG, PNG, HEIC)
- Max filstørrelse: 20 MB

---

## Filstruktur for uploads

Filer gemmes automatisk i:
```
uploads/
  2025/
    05/
      {claim_id}/
        kvittering/   ← kvitteringer
        bevis/        ← løbsbevis
```
