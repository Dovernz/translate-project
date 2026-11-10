param(
    [string]$EncFile = ".env.enc",
    [string]$OutFile = ".env",
    [string]$SampleFile = ".env.sample"
)

function Test-Decrypt([string]$Pass) {
    try {
        $fullEnc = (Resolve-Path $EncFile).Path
        $bytes = [System.IO.File]::ReadAllBytes($fullEnc)
        if ($bytes.Length -lt 29) { return $false }
        $salt = New-Object byte[](16)
        [System.Array]::Copy($bytes, 13, $salt, 0, 16)
        $cipherLen = $bytes.Length - 29
        $cipher = New-Object byte[]($cipherLen)
        [System.Array]::Copy($bytes, 29, $cipher, 0, $cipherLen)

        $kdf = New-Object System.Security.Cryptography.Rfc2898DeriveBytes($Pass, $salt, 50000, [System.Security.Cryptography.HashAlgorithmName]::SHA256)
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
        return $true
    } catch {
        return $false
    }
}

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "                KICH HOAT VA GIAI MA CAU HINH HE THONG               " -ForegroundColor Yellow
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "He thong phat hien file cau hinh ma hoa (.env.enc)."
Write-Host "Vui long nhap mat khau de tu dong giai ma cau hinh chuan (Gemini API,..."

$maxAttempts = 3
$attempt = 0

while ($attempt -lt $maxAttempts) {
    $attempt++
    Write-Host ""
    $passInput = Read-Host "Nhập mật khẩu"
    if ([string]::IsNullOrWhiteSpace($passInput)) {
        Write-Host "[!] Mat khau khong duoc de trong." -ForegroundColor Red
        continue
    }
    if ($passInput.Trim().ToLower() -eq "skip") {
        Write-Host "[*] Bo qua giai ma cau hinh ma hoa." -ForegroundColor Yellow
        break
    }

    Write-Host "[*] Dang xac thuc va giai ma... " -NoNewline
    $success = Test-Decrypt -Pass $passInput
    if ($success) {
        Write-Host "[THANH CONG]" -ForegroundColor Green
        Write-Host "[V] Da giai ma thanh cong file .env tu .env.enc!" -ForegroundColor Green
        exit 0
    } else {
        Write-Host "[THAT BAI]" -ForegroundColor Red
        Write-Host "[X] Mat khau khong chinh xac!" -ForegroundColor Red
    }
}

if (-not (Test-Path $OutFile)) {
    Write-Host ""
    Write-Host "---------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "[TUY CHON BO SUNG] Ban co muon dan truc tiep Google Gemini API Key?" -ForegroundColor Yellow
    Write-Host "Nhan phim [Y] de nhap API Key, hoac phim khac de tao file .env mau:" -ForegroundColor Yellow
    $ans = Read-Host "Lua chon (Y/N, mac dinh N)"
    if ($ans -and $ans.Trim().ToUpper() -eq "Y") {
        $apiKey = Read-Host "Dan Google Gemini API Key cua ban vao day"
        if (-not [string]::IsNullOrWhiteSpace($apiKey)) {
            $baseContent = ""
            if (Test-Path $SampleFile) {
                $baseContent = [System.IO.File]::ReadAllText((Resolve-Path $SampleFile).Path)
                $baseContent = $baseContent -replace "GEMINI_API_KEY=.*", "GEMINI_API_KEY=$($apiKey.Trim())"
            } else {
                $baseContent = "GEMINI_API_KEY=$($apiKey.Trim())`r`nPORT=8090`r`nHOST=0.0.0.0`r`n"
            }
            [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($OutFile), $baseContent)
            Write-Host "[V] Da khoi tao file .env voi API Key cua ban thanh cong!" -ForegroundColor Green
            exit 0
        }
    }

    if (Test-Path $SampleFile) {
        Copy-Item $SampleFile $OutFile -Force
        Write-Host "[V] Da khoi tao file .env tu file mau ($SampleFile)." -ForegroundColor Cyan
    } elseif (Test-Path ".env.example") {
        Copy-Item ".env.example" $OutFile -Force
        Write-Host "[V] Da khoi tao file .env tu .env.example." -ForegroundColor Cyan
    }
}
exit 0
