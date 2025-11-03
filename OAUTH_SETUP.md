# OAuth Setup for Google Drive Integration

- Uses your personal Google permissions
- Each person authorizes their own account independently
- Token auto-refreshes
- Prerequisites = Google account (@redhat.com) + 15 minutes

## One-Time Setup (Per Project/Team)

**Who does this:** Project owner or one team member

**Can be shared:** Yes, but share `oauth_credentials.json` securely (not via public repo)

### 1. Create Google Cloud Project (if needed)

Skip if project already exists.

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project → Name it (e.g., "Service Dashboard AM Team")
3. Select the project

### 2. Enable APIs

1. **APIs & Services** → **Library**
2. Enable:
   - **Google Drive API**
   - **Google Docs API**

### 3. Configure OAuth Consent Screen

1. **APIs & Services** → **OAuth consent screen**
2. Click **"Get started"** button
3. Fill in "App Information":
   - App name: `Service Dashboard`
   - Your email for support and developer contact
4. Under "Audience" select User Type: **Internal** (for Red Hat users only)
5. Then fill in "Contact Information"
6. Click **Create**

### 4. Create OAuth Client ID

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `Service Dashboard`
5. Click **Create**
6. **Download JSON** (⬇️ icon)
7. Save as: `data/oauth_credentials.json`

**Security Note:** Contains `client_secret` - share securely with team (Slack/email), don't commit to git (all json files in the `data/` folder are ignored by Git).

---

## Per-Person Setup (Everyone)

**Who does this:** Each team member on their own computer

### 1. Get OAuth Credentials

- If you created it: Already have `data/oauth_credentials.json`
- If teammate created it: Get the file from them (securely)

### 2. Authorize Your Account
(run in the active virtual environment)
```bash
python authorize_google.py
```

- Browser opens → Sign in with your Google account
- Click **Allow**
- Token saved to `data/token.json` (your personal auth, auto-refreshes)

### 3. Restart Flask & Test
(Only needed after initial authorization, not for subsequent auto-refreshes)

```bash
flask run
```

Go to: Deployments → generate the Release notes → Click **"Create Google Doc"** button 🎉

---

## For Teams

### Sharing OAuth Client

**Option 1: Share credentials securely**
- One person creates OAuth client
- Share `oauth_credentials.json` via Slack/email (not git)
- Each person runs `python authorize_google.py`

**Option 2: Each person creates their own**
- Follow "One-Time Setup"
- Completely independent

### Project Continuity (if you're leaving)

Transfer project ownership:
1. **IAM & Admin** → **IAM** → **+ Grant Access**
2. Add new owner's email → Role: **Owner**
3. They become project owner
