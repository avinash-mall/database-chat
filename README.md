# Vanna Oracle Database Chat

A natural language interface for querying Oracle databases using the Vanna AI framework with LDAP authentication.

## Quick Start

### 1. Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Oracle database credentials
```

### 2. Start the Services

```bash
# Start all containers
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
```

### 3. Initialize LDAP Users

After the containers are running, set up the LDAP users:

**Windows (PowerShell):**
```powershell
.\scripts\setup_ldap.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/setup_ldap.sh
./scripts/setup_ldap.sh
```

### 4. Access the Application

Open http://localhost:8000 in your browser and log in with:
- **Username:** `avinash`
- **Password:** `avinash123`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (Port 8000)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Vanna Flask Server                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ LDAP Auth   │  │ Chat API    │  │ Agent (LLM + Tools) │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐                ┌─────────────────────────┐
│ LDAP Server     │                │ Oracle Database         │
│ (Port 389)      │                │ (External)              │
└─────────────────┘                └─────────────────────────┘
```

## LDAP Authentication

### How It Works

1. User enters username/password on the login page
2. Frontend sends Basic Auth header to `/api/vanna/v2/auth_test`
3. Backend validates credentials against LDAP server
4. On success, cookies are set and user can access the chat

### Adding New Users

Edit `ldap_setup.ldif` to add new users:

```ldif
dn: cn=newuser,ou=users,dc=vanna,dc=ai
objectClass: inetOrgPerson
objectClass: organizationalPerson
objectClass: person
cn: newuser
sn: User
uid: newuser
userPassword: securepassword
mail: newuser@vanna.ai
```

Then re-run the setup script or manually add:

```bash
docker cp ldap_setup.ldif ldap:/tmp/ldap_setup.ldif
docker exec ldap ldapadd -x -H ldap://localhost -D "cn=admin,dc=vanna,dc=ai" -w Vanna123 -f /tmp/ldap_setup.ldif
```

### User Groups

Users can be added to groups for access control:
- **admin** - Full access to all tools including training/saving
- **user** - Can query data but cannot save training examples

Add users to the admin group in `ldap_setup.ldif`:

```ldif
dn: cn=admin,ou=groups,dc=vanna,dc=ai
objectClass: groupOfNames
cn: admin
member: cn=avinash,ou=users,dc=vanna,dc=ai
member: cn=newuser,ou=users,dc=vanna,dc=ai
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ORACLE_USER` | Oracle database username | hr |
| `ORACLE_PASSWORD` | Oracle database password | hr123 |
| `ORACLE_DSN` | Oracle connection string | localhost:1521/FREEPDB1 |
| `OLLAMA_MODEL` | Ollama model name | gpt-oss:20b |
| `OLLAMA_HOST` | Ollama server URL | http://localhost:11434 |
| `LDAP_HOST` | LDAP server hostname | ldap |
| `LDAP_PORT` | LDAP server port | 389 |
| `LDAP_ADMIN_PASSWORD` | LDAP admin password | Vanna123 |
| `VANNA_PORT` | Web server port | 8000 |

### Using OpenAI Instead of Ollama

To use OpenAI (or compatible API), set these in `.env`:

```env
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

## Troubleshooting

### LDAP Container Keeps Restarting

Check logs:
```bash
docker logs ldap
```

Common fixes:
- Remove volumes and restart: `docker-compose down -v && docker-compose up -d`
- Check `ldap_setup.ldif` for syntax errors

### Login Returns 401 Unauthorized

1. Verify LDAP is running: `docker ps | grep ldap`
2. Check if user exists:
   ```bash
   docker exec ldap ldapsearch -x -H ldap://localhost -b "dc=vanna,dc=ai" -D "cn=admin,dc=vanna,dc=ai" -w Vanna123 "(cn=avinash)"
   ```
3. Re-run the setup script

### Cannot Connect to Oracle

1. Ensure Oracle is accessible from Docker:
   - Use `host.docker.internal` instead of `localhost` in `.env`
2. Check Oracle listener is running on the specified port

## Development

### Local Development (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python -m backend.main
```

### Project Structure

```
database-chat/
├── backend/
│   ├── __init__.py
│   ├── main.py         # Flask server and LDAP auth
│   ├── config.py       # Configuration management
│   └── templates.py    # Custom login page template
├── scripts/
│   ├── setup_ldap.sh   # LDAP setup (Linux/Mac)
│   └── setup_ldap.ps1  # LDAP setup (Windows)
├── ldap_setup.ldif     # LDAP user definitions
├── docker-compose.yml  # Container orchestration
├── Dockerfile          # App container build
├── requirements.txt    # Python dependencies
└── .env.example        # Environment template
```

## License

[Your License Here]
