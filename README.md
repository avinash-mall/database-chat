# Vanna Oracle Database Chat

A natural language interface for querying Oracle databases using the Vanna AI framework with LDAP authentication. This application provides an interactive chat interface where users can query Oracle databases using plain English, powered by AI agents that understand database schemas and generate SQL queries.

## Features

- **Natural Language Queries**: Ask questions in plain English about your Oracle database
- **LDAP Authentication**: Enterprise-ready authentication with LDAP integration
- **Role-Based Access Control**: Admin, superuser, and normaluser groups with different permissions
- **Row-Level Security (RLS)**: Automatic data filtering for NORMALUSER based on AI_USERS identity columns
- **User Context Awareness**: LLM automatically knows who you are - no need to identify yourself
- **User Data Discovery**: Automatic discovery of tables containing your identity data
- **Multiple LLM Support**: Choose between Ollama (local) or OpenAI (cloud) for inference
- **Persistent Memory**: ChromaDB-based agent memory for context retention
- **Modern Web UI**: Custom-built chat interface with authentication
- **Docker Support**: Containerized deployment with Docker Compose

## Quick Start

### 1. Clone and Configure

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your Oracle database credentials and other settings
# See Configuration section below for all required variables
```

### 2. Start the Services

```bash
# Start all containers (app and LDAP server)
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
# Check logs if needed: docker-compose logs -f
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
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              ChromaDB Agent Memory                     │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────┐                ┌─────────────────────────┐
│ LDAP Server     │                │ Oracle Database         │
│ (Port 389)      │                │ (External/Configurable) │
└─────────────────┘                └─────────────────────────┘
```

## LDAP Authentication

### How It Works

1. User enters username/password on the login page
2. Frontend sends Basic Auth header to `/api/vanna/v2/auth_test`
3. Backend validates credentials against LDAP server
4. User groups are retrieved from LDAP for role-based access control
5. On success, cookies are set and user can access the chat

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

### User Groups and Roles

User roles are determined by the `AI_USERS` table in the Oracle database:

| Role | `IS_ADMIN` | `IS_SUPERUSER` | `IS_NORMALUSER` | Access Level |
|------|------------|----------------|-----------------|---------------|
| **admin** | 1 | 0 | 0 | Full access, no RLS filtering |
| **superuser** | 0 | 1 | 0 | Full access, no RLS filtering |
| **normaluser** | 0 | 0 | 1 | Row-level security applied |

### AI_USERS Table

Create the AI_USERS table in your Oracle database:

```sql
CREATE TABLE AI_USERS (
    USERNAME VARCHAR2(50) PRIMARY KEY,
    IS_ADMIN NUMBER DEFAULT 0 NOT NULL,
    IS_SUPERUSER NUMBER DEFAULT 0 NOT NULL,
    IS_NORMALUSER NUMBER DEFAULT 1 NOT NULL,
    -- Add identity columns for RLS filtering
    EMPLOYEE_ID NUMBER,
    EMAIL VARCHAR2(255),
    PERSON_ID VARCHAR2(50)
);

-- Example users
INSERT INTO AI_USERS (USERNAME, IS_ADMIN) VALUES ('avinash', 1);
INSERT INTO AI_USERS (USERNAME, IS_SUPERUSER) VALUES ('testuser', 1);
INSERT INTO AI_USERS (USERNAME, IS_NORMALUSER, EMPLOYEE_ID, EMAIL) 
    VALUES ('sarah', 1, 189, 'sarah@example.com');
```

## Row-Level Security (RLS)

### How It Works

Row-Level Security automatically filters query results for NORMALUSER based on their identity columns in AI_USERS:

1. **Dynamic Column Discovery**: The system reads AI_USERS table schema to find identity columns (any column except USERNAME, IS_ADMIN, IS_SUPERUSER, IS_NORMALUSER)
2. **Automatic Filtering**: When a NORMALUSER runs a query, WHERE clauses are injected to filter by matching columns
3. **Table Discovery**: The `discover_my_tables` tool finds tables containing user identity columns
4. **User Context**: The LLM knows who the user is and can query "my data" without asking for ID

### Example

If Sarah (EMPLOYEE_ID=189) queries the EMPLOYEES table:

```sql
-- Original query from LLM
SELECT * FROM EMPLOYEES

-- Automatically modified to:
SELECT * FROM EMPLOYEES WHERE (EMPLOYEES.EMPLOYEE_ID = :rls_param_0)
-- :rls_param_0 = 189
```

### RLS Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `RLS_ENABLED` | `true` | Enable/disable RLS filtering |
| `RLS_CACHE_TTL` | `300.0` | Cache TTL in seconds |
| `RLS_EXCLUDED_TABLES` | `""` | Comma-separated list of tables to exclude from RLS |

### Required Environment Variables

All of the following variables **must** be set in your `.env` file:

#### Oracle Database

- `ORACLE_USER` - Oracle database username
- `ORACLE_PASSWORD` - Oracle database password
- `ORACLE_DSN` - Oracle connection string (format: `host:port/service_name`)

#### Inference Provider

- `INFERENCE_PROVIDER` - Either `ollama` or `openai`

**If using Ollama:**

- `OLLAMA_MODEL` - Ollama model name (e.g., `gpt-oss:20b`)
- `OLLAMA_HOST` - Ollama server URL (e.g., `http://localhost:11434`)

**If using OpenAI:**

- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_MODEL` - OpenAI model name (e.g., `gpt-4`)

#### ChromaDB

- `CHROMA_COLLECTION` - ChromaDB collection name for agent memory
- `CHROMA_PERSIST_DIR` - Directory path for ChromaDB persistence

#### Server

- `VANNA_HOST` - Server host (typically `0.0.0.0` for Docker)
- `VANNA_PORT` - Server port (typically `8000`)

#### LDAP

- `LDAP_HOST` - LDAP server hostname (use `ldap` for Docker Compose)
- `LDAP_PORT` - LDAP server port (default: `389`)
- `LDAP_BASE_DN` - LDAP base DN (e.g., `dc=vanna,dc=ai`)
- `LDAP_USER_DN_TEMPLATE` - User DN template (e.g., `cn={username},ou=users,dc=vanna,dc=ai`)
- `LDAP_ADMIN_GROUP_DN` - Admin group DN (e.g., `cn=admin,ou=groups,dc=vanna,dc=ai`)
- `LDAP_BIND_DN` - LDAP bind DN for searches (e.g., `cn=admin,dc=vanna,dc=ai`)
- `LDAP_BIND_PASSWORD` - LDAP bind password

### Optional Environment Variables

These have defaults and can be omitted:

| Variable                      | Description                                                      | Default                               |
| ----------------------------- | ---------------------------------------------------------------- | ------------------------------------- |
| `OLLAMA_TIMEOUT`            | Ollama request timeout (seconds)                                 | `240.0`                             |
| `OLLAMA_NUM_CTX`            | Ollama context window size                                       | `8192`                              |
| `OLLAMA_TEMPERATURE`        | Ollama temperature                                               | `0.7`                               |
| `OPENAI_BASE_URL`           | OpenAI API base URL                                              | `https://api.openai.com/v1`         |
| `OPENAI_TEMPERATURE`        | OpenAI temperature                                               | `0.7` (or `0.1` for gpt-oss-120b) |
| `OPENAI_TIMEOUT`            | OpenAI request timeout (seconds)                                 | `60.0`                              |
| `LDAP_USE_SSL`              | Enable LDAP SSL                                                  | `false`                             |
| `EMAIL_DOMAIN`              | Email domain for user emails                                     | `vanna.ai`                          |
| `GUEST_USERNAME`            | Guest user username                                              | `guest`                             |
| `GUEST_EMAIL`               | Guest user email                                                 | `guest@vanna.ai`                    |
| `VANNA_LOG_LEVEL`           | Logging level                                                    | `info`                              |
| `VANNA_MAX_TOOL_ITERATIONS` | Max agent tool iterations                                        | `10`                                |
| `UI_SHOW_API_ENDPOINTS`     | Show API endpoints in UI                                         | `true`                              |
| `UI_PAGE_TITLE`             | Page title                                                       | `Agents Chat`                       |
| `UI_HEADER_TITLE`           | Header title                                                     | `Agents`                            |
| `UI_LOGIN_TITLE`            | Login form title                                                 | `Login to Continue`                 |
| `UI_CHAT_TITLE`             | Chat interface title                                             | `Oracle Database AI Chat`           |
| ...                           | (Many more UI_* variables available - see `backend/config.py`) |                                       |

### Using OpenAI Instead of Ollama

To use OpenAI (or compatible API), set these in `.env`:

```env
INFERENCE_PROVIDER=openai
OPENAI_API_KEY=sk-your-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4
```

For local or custom OpenAI-compatible endpoints:

```env
INFERENCE_PROVIDER=openai
OPENAI_API_KEY=your-api-key
OPENAI_BASE_URL=http://localhost:1234/v1
OPENAI_MODEL=your-model-name
```

## API Endpoints

The application provides several API endpoints for chat interaction:

- **POST** `/api/vanna/v2/chat_sse` - Server-Sent Events streaming
- **WS** `/api/vanna/v2/chat_websocket` - WebSocket real-time chat
- **POST** `/api/vanna/v2/chat_poll` - Request/response polling
- **POST** `/api/vanna/v2/auth_test` - LDAP authentication test
- **GET** `/health` - Health check endpoint

## Troubleshooting

### LDAP Container Keeps Restarting

Check logs:

```bash
docker logs ldap
# Or with docker-compose:
docker-compose logs ldap
```

Common fixes:

- Remove volumes and restart: `docker-compose down -v && docker-compose up -d`
- Check `ldap_setup.ldif` for syntax errors
- Verify `LDAP_ADMIN_PASSWORD` in `.env` matches `LDAP_BIND_PASSWORD`

### Login Returns 401 Unauthorized

1. Verify LDAP is running: `docker ps | grep ldap`
2. Check if user exists:
   ```bash
   docker exec ldap ldapsearch -x -H ldap://localhost -b "dc=vanna,dc=ai" -D "cn=admin,dc=vanna,dc=ai" -w Vanna123 "(cn=avinash)"
   ```
3. Verify LDAP configuration in `.env` matches docker-compose settings
4. Re-run the setup script: `./scripts/setup_ldap.sh` or `.\scripts\setup_ldap.ps1`
5. Check application logs: `docker-compose logs vanna-app`

### Cannot Connect to Oracle

1. Ensure Oracle is accessible from Docker:
   - Use `host.docker.internal` instead of `localhost` in `ORACLE_DSN` for local Oracle instances
   - Example: `ORACLE_DSN=host.docker.internal:1521/FREEPDB1`
2. Check Oracle listener is running on the specified port
3. Verify Oracle credentials are correct
4. Test connection from the container:
   ```bash
   docker exec -it vanna-app python -c "import oracledb; conn = oracledb.connect(user='YOUR_USER', password='YOUR_PASS', dsn='YOUR_DSN'); print('Connected!')"
   ```

### ChromaDB Issues

If you encounter ChromaDB errors:

1. Check that `CHROMA_PERSIST_DIR` is writable
2. The ONNX model is pre-downloaded in the Docker image, but if you're running locally, ChromaDB will download it automatically
3. Reset ChromaDB by removing the volume: `docker-compose down -v` (this deletes all agent memory)

### LLM Provider Issues

**Ollama:**

- Ensure Ollama is running and accessible at `OLLAMA_HOST`
- Check that the model is available: `curl http://localhost:11434/api/tags`
- Increase `OLLAMA_TIMEOUT` if queries are timing out

**OpenAI:**

- Verify `OPENAI_API_KEY` is set correctly
- Check API quota and rate limits
- For custom endpoints, verify `OPENAI_BASE_URL` is correct

### Application Won't Start

1. Check all required environment variables are set:
   ```bash
   # Check if .env file exists
   cat .env
   ```
2. Review startup logs:
   ```bash
   docker-compose logs vanna-app
   ```
3. Verify Python dependencies are installed (if running locally):
   ```bash
   pip install -r requirements.txt
   ```

## Development

### Local Development (without Docker)

For local development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Make sure you have Oracle Instant Client installed and configured
# For Linux: Download from Oracle and set LD_LIBRARY_PATH
# For Windows: Download and install Oracle Instant Client

# Set up environment variables (create .env file or export them)
export ORACLE_USER=your_user
export ORACLE_PASSWORD=your_password
# ... (set all required variables)

# Run the application
python -m backend.main
```

Note: For local development, you'll still need:

- LDAP server running (can use Docker Compose just for LDAP: `docker-compose up ldap -d`)
- Oracle database accessible
- Ollama or OpenAI API access

### Project Structure

```
database-chat/
├── backend/
│   ├── __init__.py
│   ├── main.py                   # Flask server, LDAP auth, and agent setup
│   ├── config.py                 # Configuration management from environment
│   ├── templates.py              # Custom login page HTML template
│   ├── rls_service.py            # Row-Level Security service
│   ├── secure_sql_tool.py        # RLS-aware SQL execution tool
│   ├── discover_tables_tool.py   # User data discovery tool
│   └── system_prompt_builder.py  # User-aware system prompts
├── assets/                       # Frontend assets
│   ├── base.html                 # Base HTML template
│   ├── css/                      # Stylesheets
│   ├── js/                       # JavaScript files (auth, chat, components)
│   └── fonts/                    # Custom fonts
├── scripts/
│   ├── setup_ldap.sh             # LDAP setup script (Linux/Mac)
│   └── setup_ldap.ps1            # LDAP setup script (Windows)
├── chroma_db/                    # ChromaDB persistence directory (created at runtime)
├── ldap_setup.ldif               # LDAP user and group definitions
├── docker-compose.yml            # Container orchestration
├── Dockerfile                    # App container build definition
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

### Key Components

- **`backend/main.py`**:

  - Custom Flask server extending VannaFlaskServer
  - LDAP authentication via `LdapUserResolver`
  - Agent creation with Oracle, LLM, and ChromaDB integration
  - Custom routes for authentication and static assets
- **`backend/config.py`**:

  - Comprehensive configuration management
  - Loads from environment variables
  - Supports both Ollama and OpenAI inference providers
  - UI text customization
- **`backend/templates.py`**:

  - Generates custom login HTML
  - Loads assets from filesystem
  - Injects configuration into templates

### Building and Running with Docker

```bash
# Build the image
docker-compose build

# Run in foreground (for debugging)
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f vanna-app

# Stop services
docker-compose down

# Stop and remove volumes (clears ChromaDB and LDAP data)
docker-compose down -v
```

## Agent Capabilities

The Vanna Agent provides several tools based on user permissions:

**All Users (admin, superuser, normaluser):**

- `run_sql` - Execute SQL queries on Oracle database (RLS applied for normaluser)
- `discover_my_tables` - Discover tables containing user identity columns
- `search_saved_correct_tool_uses` - Search past successful queries
- `save_text_memory` - Save text-based memories
- `visualize_data` - Create visualizations from query results

**Admin and Superuser Only:**

- `save_question_tool_args` - Save training examples for query improvement

### User Context in LLM

The LLM automatically knows:
- User's username, email, and groups
- User's identity column values (EMPLOYEE_ID, EMAIL, etc.)
- Access level (full access or RLS-restricted)

This allows natural queries like "show me my employee details" without needing to specify user ID.

## Security Considerations

- **Row-Level Security**: NORMALUSER can only see data matching their identity columns
- **SQL Injection Prevention**: RLS filters use parameterized queries
- **LDAP Passwords**: Store LDAP passwords securely and never commit `.env` files
- **Oracle Credentials**: Use strong passwords and consider using Oracle wallet for credential management
- **API Keys**: Keep OpenAI API keys secure and rotate them regularly
- **Network**: In production, use SSL/TLS for LDAP (`LDAP_USE_SSL=true`)
- **Access Control**: Regularly review AI_USERS table and LDAP group memberships

## License

MIT License
