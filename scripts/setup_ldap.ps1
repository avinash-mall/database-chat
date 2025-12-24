# LDAP User Setup Script (PowerShell)
# This script initializes/updates the LDAP server with users and groups from ldap_setup.ldif
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
    }
    catch {}
    
    if ($i -eq $MAX_RETRIES) {
        Write-Host "ERROR: LDAP server did not become ready in time"
        exit 1
    }
    Write-Host "  Attempt $i/$MAX_RETRIES - waiting ${RETRY_DELAY}s..."
    Start-Sleep -Seconds $RETRY_DELAY
}

# Copy LDIF file to container
Write-Host "Copying $LDIF_FILE to container..."
docker cp $LDIF_FILE "${LDAP_CONTAINER}:/tmp/ldap_setup.ldif"

# Parse LDIF and add entries one by one (to handle partial updates)
Write-Host ""
Write-Host "Processing LDAP entries..."
Write-Host "---------------------------------------------------"

# Read the LDIF file content
$ldifContent = Get-Content -Path $LDIF_FILE -Raw

# Split into individual entries (separated by blank lines)
$entries = $ldifContent -split "`r?`n`r?`n" | Where-Object { $_.Trim() -ne "" }

$added = 0
$skipped = 0
$failed = 0

foreach ($entry in $entries) {
    # Extract DN from the entry
    if ($entry -match "^dn:\s*(.+)$" -or $entry -match "(?m)^dn:\s*(.+)$") {
        $dn = $matches[1].Trim()
        
        # Check if entry already exists
        $checkResult = docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b $dn -s base -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(objectClass=*)" 2>&1
        
        if ($checkResult -match "dn: $([regex]::Escape($dn))") {
            Write-Host "  [SKIP] $dn (already exists)"
            $skipped++
        }
        else {
            # Entry doesn't exist, try to add it
            $tempFile = [System.IO.Path]::GetTempFileName()
            # Convert entry to have proper line endings for LDIF
            $entryContent = $entry -replace "`r`n", "`n"
            [System.IO.File]::WriteAllText($tempFile, $entryContent + "`n")
            
            # Copy single entry to container
            docker cp $tempFile "${LDAP_CONTAINER}:/tmp/single_entry.ldif" 2>&1 | Out-Null
            Remove-Item $tempFile -Force
            
            # Try to add the entry
            $addResult = docker exec $LDAP_CONTAINER ldapadd -x -H ldap://localhost -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD -f /tmp/single_entry.ldif 2>&1
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [ADD]  $dn"
                $added++
            }
            else {
                Write-Host "  [FAIL] $dn - $($addResult | Out-String)"
                $failed++
            }
        }
    }
}

Write-Host "---------------------------------------------------"
Write-Host ""
Write-Host "==================================================="
Write-Host "LDAP setup complete!"
Write-Host "==================================================="
Write-Host ""
Write-Host "Summary: Added=$added, Skipped=$skipped, Failed=$failed"
Write-Host ""
Write-Host "Current users:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=users,dc=vanna,dc=ai" -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(objectClass=inetOrgPerson)" cn mail 2>&1 | Select-String -Pattern "^(dn:|cn:|mail:)"
Write-Host ""
Write-Host "Current groups:"
docker exec $LDAP_CONTAINER ldapsearch -x -H ldap://localhost -b "ou=groups,dc=vanna,dc=ai" -D $LDAP_ADMIN_DN -w $LDAP_ADMIN_PASSWORD "(objectClass=groupOfNames)" cn 2>&1 | Select-String -Pattern "^(dn:|cn:)"
