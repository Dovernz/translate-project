param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("encrypt", "decrypt")]
    [string]$Action,
    [string]$MasterPass = "",
    [string]$UserPass = "",
    [string]$Password = "",
    [string]$InFile = ".env",
    [string]$OutFile = ".env.enc"
)

$ErrorActionPreference = "Stop"

if ($Action -eq "encrypt") {
    if ([string]::IsNullOrWhiteSpace($MasterPass) -or [string]::IsNullOrWhiteSpace($UserPass)) {
        Write-Error "Action 'encrypt' requires both -MasterPass and -UserPass parameters to be provided."
        exit 1
    }
    if (-not (Test-Path $InFile)) {
        Write-Error "Source file does not exist: $InFile"
        exit 1
    }
    $plain = [System.IO.File]::ReadAllBytes((Resolve-Path $InFile).Path)
    
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $dataKey = New-Object byte[](32)
    $dataIV = New-Object byte[](16)
    $rng.GetBytes($dataKey)
    $rng.GetBytes($dataIV)

    $aesData = [System.Security.Cryptography.Aes]::Create()
    $aesData.KeySize = 256
    $aesData.BlockSize = 128
    $aesData.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $aesData.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
    $aesData.Key = $dataKey
    $aesData.IV = $dataIV
    $cipherPayload = $aesData.CreateEncryptor().TransformFinalBlock($plain, 0, $plain.Length)

    # Master Slot
    $saltM = New-Object byte[](16); $rng.GetBytes($saltM)
    $kdfM = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($MasterPass, $saltM, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $aesM = [System.Security.Cryptography.Aes]::Create()
    $aesM.Key = $kdfM.GetBytes(32)
    $aesM.IV = $kdfM.GetBytes(16)
    $cipherKeyM = $aesM.CreateEncryptor().TransformFinalBlock($dataKey, 0, $dataKey.Length)

    # User Slot
    $saltU = New-Object byte[](16); $rng.GetBytes($saltU)
    $kdfU = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($UserPass, $saltU, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $aesU = [System.Security.Cryptography.Aes]::Create()
    $aesU.Key = $kdfU.GetBytes(32)
    $aesU.IV = $kdfU.GetBytes(16)
    $cipherKeyU = $aesU.CreateEncryptor().TransformFinalBlock($dataKey, 0, $dataKey.Length)

    # File Pack
    $magic = [System.Text.Encoding]::ASCII.GetBytes("GEMINI_DUAL_V1")
    $outResolved = [System.IO.Path]::GetFullPath($OutFile)
    $fs = [System.IO.File]::Create($outResolved)
    $fs.Write($magic, 0, $magic.Length)
    $fs.Write($saltM, 0, $saltM.Length)
    $fs.Write($cipherKeyM, 0, $cipherKeyM.Length)
    $fs.Write($saltU, 0, $saltU.Length)
    $fs.Write($cipherKeyU, 0, $cipherKeyU.Length)
    $fs.Write($dataIV, 0, $dataIV.Length)
    $fs.Write($cipherPayload, 0, $cipherPayload.Length)
    $fs.Close()

    Write-Output "DUAL_ENCRYPTION_OK"
}
elseif ($Action -eq "decrypt") {
    if (-not (Test-Path $InFile)) {
        Write-Error "Encrypted file does not exist: $InFile"
        exit 1
    }
    $bytes = [System.IO.File]::ReadAllBytes((Resolve-Path $InFile).Path)
    $magicStr = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 14)
    if ($magicStr -ne "GEMINI_DUAL_V1") {
        Write-Error "Invalid dual encrypted format."
        exit 2
    }

    $offset = 14
    $sM = New-Object byte[](16); [System.Array]::Copy($bytes, $offset, $sM, 0, 16); $offset += 16
    $ckM = New-Object byte[](48); [System.Array]::Copy($bytes, $offset, $ckM, 0, 48); $offset += 48

    $sU = New-Object byte[](16); [System.Array]::Copy($bytes, $offset, $sU, 0, 16); $offset += 16
    $ckU = New-Object byte[](48); [System.Array]::Copy($bytes, $offset, $ckU, 0, 48); $offset += 48

    $dIV = New-Object byte[](16); [System.Array]::Copy($bytes, $offset, $dIV, 0, 16); $offset += 16

    $pLen = $bytes.Length - $offset
    $pData = New-Object byte[]($pLen); [System.Array]::Copy($bytes, $offset, $pData, 0, $pLen)

    $dk = $null
    # Try Master Slot
    try {
        $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Password, $sM, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
        $aes = [System.Security.Cryptography.Aes]::Create()
        $aes.Key = $kdf.GetBytes(32)
        $aes.IV = $kdf.GetBytes(16)
        $cand = $aes.CreateDecryptor().TransformFinalBlock($ckM, 0, $ckM.Length)
        if ($cand.Length -eq 32) { $dk = $cand }
    } catch {}

    # Try User Slot
    if ($dk -eq $null) {
        try {
            $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Password, $sU, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
            $aes = [System.Security.Cryptography.Aes]::Create()
            $aes.Key = $kdf.GetBytes(32)
            $aes.IV = $kdf.GetBytes(16)
            $cand = $aes.CreateDecryptor().TransformFinalBlock($ckU, 0, $ckU.Length)
            if ($cand.Length -eq 32) { $dk = $cand }
        } catch {}
    }

    if ($dk -eq $null) {
        Write-Error "Invalid password."
        exit 3
    }

    $aesFinal = [System.Security.Cryptography.Aes]::Create()
    $aesFinal.Key = $dk
    $aesFinal.IV = $dIV
    $decrypted = $aesFinal.CreateDecryptor().TransformFinalBlock($pData, 0, $pData.Length)

    $outResolved = [System.IO.Path]::GetFullPath($OutFile)
    [System.IO.File]::WriteAllBytes($outResolved, $decrypted)
    Write-Output "DECRYPTION_OK"
}
