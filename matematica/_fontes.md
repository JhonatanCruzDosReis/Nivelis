# Fatos matemáticos verificados

Diferente das disciplinas factuais, aqui as respostas são CALCULADAS
pelo próprio gerador — não vêm de tabela. O risco não é o fato errado,
e sim a fórmula errada. Por isso o que se verifica são as fórmulas.

---

## Progressão aritmética

| Grandeza | Fórmula |
|---|---|
| termo geral | aₙ = a₁ + (n − 1)·r |
| soma dos n primeiros | Sₙ = n·(a₁ + aₙ) / 2 |
| razão | r = aₙ − aₙ₋₁ |

**Classificação pela razão:** r > 0 crescente; r < 0 decrescente;
r = 0 constante.

**Propriedade:** cada termo, a partir do segundo, é a média aritmética
dos vizinhos.

---

## Progressão geométrica

| Grandeza | Fórmula |
|---|---|
| termo geral | aₙ = a₁ · q^(n−1) |
| soma dos n primeiros | Sₙ = a₁·(qⁿ − 1) / (q − 1), com q ≠ 1 |
| soma infinita | S = a₁ / (1 − q), somente para \|q\| < 1 |
| razão | q = aₙ / aₙ₋₁ |

**Classificação:**
- crescente: q > 1 com termos positivos, ou 0 < q < 1 com termos negativos
- decrescente: 0 < q < 1 com termos positivos, ou q > 1 com termos negativos
- oscilante ou alternante: q < 0
- constante: q = 1

**Propriedade:** cada termo, a partir do segundo, é a média geométrica
dos vizinhos.

⚠️ ARMADILHAS DE PROVA:
- A soma infinita SÓ EXISTE quando |q| < 1. Fora disso a série diverge.
- Na fórmula do termo geral o expoente é n−1, não n — o erro mais
  comum é usar qⁿ.
- Classificar a PG exige olhar o SINAL DOS TERMOS junto com a razão:
  q > 1 com termos negativos produz sequência decrescente.

Fontes: eduCAPES (Progressão Aritmética e Geométrica); Toda Matéria;
Estratégia Militares; ValorFinal (revisado, referência OBMEP/IMPA);
Prof. Walter Tadeu — Colégio Pedro II.
