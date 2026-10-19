$Project = "C:\Users\owner\OneDrive\Desktop\clan_registry"
$BackupRoot = "C:\Users\owner\OneDrive\Desktop\clan_registry_backups"
$GoogleDriveRoot = "G:\My Drive\UMUOTUTO Registry Backups"

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

$LocalBackup = Join-Path $BackupRoot "backup_$Timestamp"
$OnlineBackup = Join-Path $GoogleDriveRoot "backup_$Timestamp"

# Create local backup folder
New-Item -ItemType Directory -Path $LocalBackup -Force | Out-Null

# Copy project to local backup
Copy-Item "$Project\*" $LocalBackup -Recurse -Force

Write-Host "Local backup completed:"
Write-Host $LocalBackup

# Copy local backup to Google Drive
if (Test-Path $GoogleDriveRoot) {

    Copy-Item $LocalBackup $OnlineBackup -Recurse -Force

    Write-Host "Google Drive backup completed:"
    Write-Host $OnlineBackup

} else {

    Write-Host "WARNING: Google Drive is not available."
    Write-Host "Local backup was completed, but online backup was NOT created."
}

# Keep only the 3 newest local backups
$Backups = Get-ChildItem $BackupRoot -Directory |
    Where-Object { $_.Name -like "backup_*" } |
    Sort-Object LastWriteTime -Descending

if ($Backups.Count -gt 3) {

    $Backups | Select-Object -Skip 3 | ForEach-Object {
        Remove-Item $_.FullName -Recurse -Force
        Write-Host "Removed old local backup:"
        Write-Host $_.FullName
    }
}