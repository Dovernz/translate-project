param(
    [string]$EncFile = ".env.enc",
    [string]$OutFile = ".env",
    [string]$SampleFile = ".env.example"
)

function Test-Decrypt([string]$Pass) {
    try {
        $fullEnc = (Resolve-Path $EncFile).Path
        $bytes = [System.IO.File]::ReadAllBytes($fullEnc)
        if ($bytes.Length -lt 158) { return $false }
        $magicStr = [System.Text.Encoding]::ASCII.GetString($bytes, 0, 14)
        if ($magicStr -ne "GEMINI_DUAL_V1") { return $false }

        $offset = 14
        $sM = New-Object byte[](16); [System.Array]::Copy($bytes, $offset, $sM, 0, 16); $offset += 16
        $ckM = New-Object byte[](48); [System.Array]::Copy($bytes, $offset, $ckM, 0, 48); $offset += 48

        $sU = New-Object byte[](16); [System.Array]::Copy($bytes, $offset, $sU, 0, 16); $offset += 16
        $ckU = New-Object byte[](48); [System.Array]::Copy($bytes, $offset, $ckU, 0, 48); $offset += 48

        $dIV = New-Object byte[](16); [System.Array]::Copy($bytes, $offset, $dIV, 0, 16); $offset += 16

        $pLen = $bytes.Length - $offset
        $pData = New-Object byte[]($pLen); [System.Array]::Copy($bytes, $offset, $pData, 0, $pLen)

        $dk = $null
        try {
            $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Pass, $sM, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
            $aes = [System.Security.Cryptography.Aes]::Create()
            $aes.Key = $kdf.GetBytes(32)
            $aes.IV = $kdf.GetBytes(16)
            $cand = $aes.CreateDecryptor().TransformFinalBlock($ckM, 0, $ckM.Length)
            if ($cand.Length -eq 32) { $dk = $cand }
        } catch {}

        if ($dk -eq $null) {
            try {
                $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Pass, $sU, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
                $aes = [System.Security.Cryptography.Aes]::Create()
                $aes.Key = $kdf.GetBytes(32)
                $aes.IV = $kdf.GetBytes(16)
                $cand = $aes.CreateDecryptor().TransformFinalBlock($ckU, 0, $ckU.Length)
                if ($cand.Length -eq 32) { $dk = $cand }
            } catch {}
        }

        if ($dk -eq $null) { return $false }

        $aesFinal = [System.Security.Cryptography.Aes]::Create()
        $aesFinal.Key = $dk
        $aesFinal.IV = $dIV
        $decrypted = $aesFinal.CreateDecryptor().TransformFinalBlock($pData, 0, $pData.Length)

        $outFull = [System.IO.Path]::GetFullPath($OutFile)
        [System.IO.File]::WriteAllBytes($outFull, $decrypted)
        return $true
    } catch {
        return $false
    }
}

$maxAttempts = 3
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    $passInput = Read-Host "Nhập mật khẩu"
    if ([string]::IsNullOrWhiteSpace($passInput)) {
        continue
    }

    $success = Test-Decrypt -Pass $passInput
    if ($success) {
        Write-Host "Giải mã thành công." -ForegroundColor Green
        exit 0
    } else {
        Write-Host "Mật khẩu không chính xác." -ForegroundColor Red
    }
}

if (-not (Test-Path $OutFile)) {
    if (Test-Path $SampleFile) {
        Copy-Item $SampleFile $OutFile -Force
    }
}
exit 0
