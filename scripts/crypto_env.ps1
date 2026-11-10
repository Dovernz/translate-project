param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("encrypt", "decrypt")]
    [string]$Action,
    [Parameter(Mandatory=$true)]
    [string]$Password,
    [string]$InFile = ".env",
    [string]$OutFile = ".env.enc"
)

$ErrorActionPreference = "Stop"

if ($Action -eq "encrypt") {
    if (-not (Test-Path $InFile)) {
        Write-Error "Source file does not exist: $InFile"
        exit 1
    }
    $inResolved = (Resolve-Path $InFile).Path
    $plain = [System.IO.File]::ReadAllBytes($inResolved)
    $salt = New-Object byte[](16)
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($salt)

    $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Password, $salt, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
    $key = $kdf.GetBytes(32)
    $iv = $kdf.GetBytes(16)

    $aes = [System.Security.Cryptography.Aes]::Create()
    $aes.KeySize = 256
    $aes.BlockSize = 128
    $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
    $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
    $aes.Key = $key
    $aes.IV = $iv

    $encryptor = $aes.CreateEncryptor()
    $cipher = $encryptor.TransformFinalBlock($plain, 0, $plain.Length)

    $outFull = [System.IO.Path]::GetFullPath($OutFile)
    $fs = [System.IO.File]::Create($outFull)
    $magic = [System.Text.Encoding]::ASCII.GetBytes("GEMINI_ENC_V1")
    $fs.Write($magic, 0, $magic.Length)
    $fs.Write($salt, 0, $salt.Length)
    $fs.Write($cipher, 0, $cipher.Length)
    $fs.Close()
    Write-Output "ENCRYPTION_OK"
}
elseif ($Action -eq "decrypt") {
    if (-not (Test-Path $InFile)) {
        Write-Error "Encrypted file does not exist: $InFile"
        exit 1
    }
    $inResolved = (Resolve-Path $InFile).Path
    $bytes = [System.IO.File]::ReadAllBytes($inResolved)
    if ($bytes.Length -lt 29) {
        Write-Error "Invalid encrypted file length."
        exit 2
    }
    $magic = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 13)
    if ($magic -ne "GEMINI_ENC_V1") {
        Write-Error "Invalid header magic."
        exit 2
    }
    $salt = New-Object byte[](16)
    [System.Array]::Copy($bytes, 13, $salt, 0, 16)
    $cipherLen = $bytes.Length - 29
    $cipher = New-Object byte[]($cipherLen)
    [System.Array]::Copy($bytes, 29, $cipher, 0, $cipherLen)

    try {
        $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Password, $salt, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
        $key = $kdf.GetBytes(32)
        $iv = $kdf.GetBytes(16)

        $aes = [System.Security.Cryptography.Aes]::Create()
        $aes.KeySize = 256
        $aes.BlockSize = 128
        $aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
        $aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
        $aes.Key = $key
        $aes.IV = $iv

        $decryptor = $aes.CreateDecryptor()
        $decrypted = $decryptor.TransformFinalBlock($cipher, 0, $cipher.Length)
        
        $outFull = [System.IO.Path]::GetFullPath($OutFile)
        [System.IO.File]::WriteAllBytes($outFull, $decrypted)
        Write-Output "DECRYPTION_OK"
    } catch {
        Write-Error "DECRYPTION_FAILED: Invalid password or corrupted data."
        exit 3
    }
}
