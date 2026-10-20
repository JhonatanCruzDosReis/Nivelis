"""
=============================================================
  TESTE — Diagnóstico do .env
=============================================================
  Rode este script DENTRO da pasta Nivelis-Api:

      python teste_env.py

  Ele vai te dizer EXATAMENTE o que está errado.
=============================================================
"""

import os
import sys

print("\n" + "="*60)
print("  DIAGNÓSTICO DO .env")
print("="*60 + "\n")

# 1. Verifica pasta atual
print(f"📁 Pasta atual: {os.getcwd()}")

# 2. Verifica se o .env existe
env_existe = os.path.isfile(".env")
print(f"📄 .env existe? {env_existe}")

if not env_existe:
    print("\n❌ O arquivo .env NÃO está nesta pasta!")
    print("   Você precisa estar dentro da pasta Nivelis-Api ao rodar.")
    sys.exit(1)

# 3. Lê o conteúdo bruto do .env
print(f"\n📋 Conteúdo bruto do .env:")
print("-" * 40)
with open(".env", "rb") as f:
    conteudo_bytes = f.read()
    print(f"   Tamanho: {len(conteudo_bytes)} bytes")
    print(f"   Bytes (primeiros 100): {conteudo_bytes[:100]}")
print("-" * 40)

# 4. Verifica se tem BOM
if conteudo_bytes.startswith(b'\xef\xbb\xbf'):
    print("\n⚠️  O arquivo TEM BOM (UTF-8 com BOM) — isso pode causar problema!")
elif conteudo_bytes.startswith(b'\xff\xfe'):
    print("\n⚠️  O arquivo está em UTF-16 — precisa ser UTF-8!")
else:
    print("\n✅ Arquivo está em UTF-8 puro (sem BOM)")

# 5. Tenta carregar com python-dotenv
print("\n🔧 Testando python-dotenv...")
try:
    from dotenv import load_dotenv
    resultado = load_dotenv()
    print(f"   load_dotenv() retornou: {resultado}")
except ImportError:
    print("   ❌ python-dotenv NÃO está instalado!")
    print("      Roda: pip install python-dotenv")
    sys.exit(1)

# 6. Tenta pegar a variável
chave = os.getenv("GEMINI_API_KEY")
print(f"\n🔑 Valor de GEMINI_API_KEY:")
if chave:
    print(f"   ✅ Encontrada! Começa com: {chave[:10]}...")
    print(f"   Tamanho: {len(chave)} caracteres")
else:
    print(f"   ❌ NÃO encontrada (None)")

# 7. Lista TODAS as variáveis carregadas do .env
print(f"\n📦 Todas as variáveis disponíveis (que começam com 'GEMI' ou 'NIVE'):")
for k, v in os.environ.items():
    if k.startswith(("GEMI", "NIVE", "GNEW")):
        print(f"   {k} = {v[:15]}...")

print("\n" + "="*60 + "\n")
