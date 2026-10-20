# ============================================================
# NIVELIS - Script de build do APK via EAS Cloud
# Execute com: botao direito > "Executar com PowerShell"
# ============================================================

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectDir

Write-Host ""
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "  NIVELIS - Build APK (EAS Cloud)" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host ""

# 1. Verifica eas-cli
Write-Host "[1/4] Verificando eas-cli..." -ForegroundColor Cyan
$easVersion = eas --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Instalando eas-cli..." -ForegroundColor Yellow
    npm install -g eas-cli
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERRO: Falha ao instalar eas-cli." -ForegroundColor Red
        Read-Host "Pressione Enter para fechar"
        exit 1
    }
} else {
    Write-Host "  eas-cli: $easVersion" -ForegroundColor Green
}

# 2. Verifica login
Write-Host ""
Write-Host "[2/4] Verificando login no Expo..." -ForegroundColor Cyan
$whoami = eas whoami 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Faca login:" -ForegroundColor Yellow
    eas login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERRO: Login falhou." -ForegroundColor Red
        Read-Host "Pressione Enter para fechar"
        exit 1
    }
} else {
    Write-Host "  Logado como: $whoami" -ForegroundColor Green
}

# 3. Instala dependencias (incluindo expo-build-properties)
Write-Host ""
Write-Host "[3/4] Instalando dependencias npm..." -ForegroundColor Cyan
npm install --legacy-peer-deps
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Aviso: npm install retornou erros, continuando..." -ForegroundColor Yellow
}
Write-Host "  Dependencias instaladas!" -ForegroundColor Green

# 4. Build APK
Write-Host ""
Write-Host "[4/4] Iniciando build do APK (profile: preview)..." -ForegroundColor Cyan
Write-Host "  Build na nuvem EAS. Aguarde o link de download." -ForegroundColor White
Write-Host ""

eas build --platform android --profile preview

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "  BUILD CONCLUIDO! Baixe o APK pelo link acima." -ForegroundColor Green
    Write-Host "  Ou acesse: https://expo.dev" -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Build falhou. Acesse o link de logs exibido acima para detalhes." -ForegroundColor Red
}

Write-Host ""
Read-Host "Pressione Enter para fechar"
