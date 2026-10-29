param(
    [string]$Target = "C:\DeskEcho\DeskEcho.exe",
    [string]$Arguments = ""
)

$shellWindows = (New-Object -ComObject Shell.Application).Windows()
# Get the desktop browser object
$shellFolderView = $null
try {
    $desktop = $shellWindows.FindWindowSW([ref]0, [ref]0, 8, [ref]0, 1)
    if ($desktop) {
        $dispatch = $desktop.Document.Application
        Write-Host "[*] Got desktop Dispatch, calling ShellExecute with $Target..."
        $dispatch.ShellExecute($Target, $Arguments, "C:\DeskEcho", "open", 1)
        Write-Host "[+] ShellExecute completed successfully!"
        exit 0
    }
} catch {
    Write-Host "[-] Method 1 error: $_"
}

# Method 2: Shell.Application directly
try {
    $sh = New-Object -ComObject Shell.Application
    $sh.ShellExecute($Target, $Arguments, "C:\DeskEcho", "open", 1)
    Write-Host "[+] Shell.Application ShellExecute succeeded"
    exit 0
} catch {
    Write-Host "[-] Method 2 error: $_"
}
exit 1
