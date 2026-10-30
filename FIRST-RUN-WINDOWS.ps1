# BridgeLab first-run runtime setup. No administrator privileges or PATH changes.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$runtime = Join-Path $env:LOCALAPPDATA 'BridgeLab\runtime\Python312'
$python = Join-Path $runtime 'python.exe'
$installerDirectory = $null
function Test-BridgePython([string]$Executable, [string[]]$Prefix = @()) {
    try {
        & $Executable @Prefix -c "import sys; assert sys.version_info >= (3,11); import tkinter; t = tkinter.Tcl()" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}
try {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'This package requires 64-bit Windows.' }
    # Keep direct invocation consistent with the launcher: reuse a suitable local
    # Python before installing a dedicated runtime.
    if (-not (Test-BridgePython $python)) {
        foreach ($command in @('py.exe', 'python.exe')) {
            $candidate = Get-Command $command -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
            $prefix = @()
            if ($command -eq 'py.exe') { $prefix = @('-3') }
            if ($candidate -and (Test-BridgePython $candidate.Source $prefix)) {
                & $candidate.Source @prefix -u (Join-Path $root 'launch_bridge.py')
                if ($LASTEXITCODE -ne 0) { throw "BridgeLab exited with code $LASTEXITCODE." }
                exit 0
            }
        }
    }
    if (-not (Test-BridgePython $python)) {
        $installerDirectory = Join-Path $env:TEMP ('bridgelab-setup-' + [Guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $installerDirectory | Out-Null
        $installer = Join-Path $installerDirectory 'python-3.12.10-amd64.exe'
        # Pinned official python.org installer. Hash and Authenticode are checked
        # before execution; the installer itself is not included in the package.
        $expected = '67b5635e80ea51072b87941312d00ec8927c4db9ba18938f7ad2d27b328b95fb'
        $installerUrl = 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
        Write-Host 'Python 3.12.10 is missing. Downloading the official installer (about 26 MB)...'
        try {
            [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
            Invoke-WebRequest -Uri $installerUrl -OutFile $installer -UseBasicParsing
        } catch {
            Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
            throw 'Could not download the verified Python installer. Check your internet connection and launch BridgeLab again.'
        }
        if ($expected -notmatch '^[0-9a-f]{64}$') { throw 'Invalid pinned Python installer checksum.' }
        $actual = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue; throw 'Python installer checksum mismatch. Setup stopped.' }
        $signature = Get-AuthenticodeSignature -LiteralPath $installer
        if ($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate -or
            $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Python Software Foundation(,|$)') {
            Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
            throw 'Python installer must have a valid Python Software Foundation Authenticode signature. Setup stopped.'
        }
        Write-Host 'BridgeLab will now automatically set up Python for your Windows user.'
        Write-Host "Runtime location: $runtime"
        Write-Host 'No administrator privileges, PATH changes, or file associations are requested.'
        $arguments = '/quiet InstallAllUsers=0 TargetDir="' + $runtime + '" Include_tcltk=1 Include_pip=0 Include_test=0 Include_doc=0 Include_launcher=0 AssociateFiles=0 PrependPath=0 Shortcuts=0'
        $process = Start-Process -FilePath $installer -ArgumentList $arguments -Wait -PassThru
        Remove-Item -LiteralPath $installer -Force -ErrorAction SilentlyContinue
        if ($process.ExitCode -notin @(0, 3010)) {
            throw "Python setup failed with exit code $($process.ExitCode)."
        }
        if ($process.ExitCode -eq 3010) { Write-Host 'Python setup reports that Windows may need a restart.' }
        if (-not (Test-BridgePython $python)) {
            throw 'Python/Tcl-Tk verification failed after setup. Restart Windows if requested, then launch BridgeLab again.'
        }
    }
    & $python -u (Join-Path $root 'launch_bridge.py')
    if ($LASTEXITCODE -ne 0) { throw "BridgeLab exited with code $LASTEXITCODE." }
    exit 0
} catch {
    Write-Host "BridgeLab setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
} finally {
    if ($installerDirectory -and (Test-Path -LiteralPath $installerDirectory)) {
        Remove-Item -LiteralPath $installerDirectory -Recurse -Force -ErrorAction SilentlyContinue
    }
}
