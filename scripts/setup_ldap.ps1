# LDAP User Setup Script (PowerShell)
# This script initializes the LDAP server with users and groups from ldap_setup.ldif
# Run this after starting the containers with: docker-compose up -d

$ErrorActionPreference = "Stop"

$LDAP_CONTAINER = "ldap"
$LDAP_ADMIN_DN = "cn=admin,dc=vanna,dc=ai"
$LDAP_ADMIN_PASSWORD = if ($env:LDAP_ADMIN_PASSWORD) { $env:LDAP_ADMIN_PASSWORD } else { "Vanna123" }
$LDIF_FILE = "ldap_setup.ldif"
$MAX_RETRIES = 30
$RETRY_DELAY = 2

Write-Host "==================================================="
Write-Host "LDAP User Setup Script"
Write-Host "==================================================="

# Wait for LDAP container to be ready
Write-Host "Waiting for LDAP container to be ready..."
for ($i = 1; $i -le $MAX_RETRIES; $i++) {
    try {
        $result = docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "dc=vanna,dc=ai" -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(objectClass=*)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "LDAP server is ready!"
            break
        }
    } catch {}
    
    if ($i -eq $MAX_RETRIES) {
        Write-Host "ERROR: LDAP server did not become ready in time"
        exit 1
    }
    Write-Host "  Attempt $i/$MAX_RETRIES - waiting ${RETRY_DELAY}s..."
    Start-Sleep -Seconds $RETRY_DELAY
}

# Check if users already exist
Write-Host "Checking if users already exist..."
$userCheck = docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "dc=vanna,dc=ai" -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(cn=avinash)" 2>&1
if ($userCheck -match "cn: avinash") {
    Write-Host "Users already exist in LDAP. Skipping import."
    Write-Host "To re-import, first delete existing entries or recreate volumes with: docker-compose down -v"
    exit 0
}

# Copy LDIF file to container
Write-Host "Copying $LDIF_FILE to container..."
docker cp $LDIF_FILE "${LDAP_CONTAINER}:/tmp/ldap_setup.ldif"

# Import LDIF
Write-Host "Importing LDAP entries..."
docker exec $LDAP_CONTAINER ldapadd -x -H ldap://localhost -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD -f /tmp/ldap_setup.ldif

Write-Host ""
Write-Host "==================================================="
Write-Host "LDAP setup complete!"
Write-Host "==================================================="
Write-Host ""
Write-Host "Users created:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=users,dc=vanna,dc=ai" -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(objectClass=inetOrgPerson)" cn mail 2>&1 | Select-String -Pattern "^(dn:|cn:|mail:)"
Write-Host ""
Write-Host "Groups created:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=groups,dc=vanna,dc=ai" -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(objectClass=groupOfNames)" cn 2>&1 | Select-String -Pattern "^(dn:|cn:)"
