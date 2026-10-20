/*
==============================================================
  COMO ADICIONAR O CARD "QUESTÕES" NO ACESSO RÁPIDO
==============================================================

CONTEXTO:
A tela "Início" (que tem o Acesso Rápido com Cronograma/Simulados/
Livros/Matérias) — você NÃO me enviou esse arquivo, então não posso
editar diretamente. Mas o snippet abaixo é o card pronto pra colar.

PASSOS:

1. Abre o arquivo da tela "Início" no seu PC. Provavelmente é algo como:
     - app/(tabs)/index.tsx
     - app/inicio.tsx
     - app/home.tsx
   (procure pelo arquivo que tem o JSX com "Acesso Rápido")

2. Localiza o último card do Acesso Rápido (provavelmente "Matérias")

3. COLA o JSX abaixo logo APÓS o card de Matérias (ou onde quiser).
   Ajusta a navegação conforme o teu sistema:
     - Se usa expo-router:   router.push('/questoes')
     - Se usa react-navigation: navigation.navigate('Questoes')

==============================================================
  JSX DO CARD (cola dentro do grid do Acesso Rápido):
==============================================================
*/

<TouchableOpacity
  style={styles.card}
  onPress={() => navigation.navigate('Questoes')}
  activeOpacity={0.7}
>
  <View style={[styles.cardIconBox, { backgroundColor: '#F59E0B20' }]}>
    <Ionicons name="help-circle-outline" size={32} color="#F59E0B" />
  </View>
  <Text style={styles.cardTitulo}>Questões</Text>
  <Text style={styles.cardDesc}>Pratique uma por vez</Text>
</TouchableOpacity>


/*
==============================================================
  IMPORTANTE — VERIFICA OS ESTILOS
==============================================================

O snippet acima usa estilos como "styles.card", "styles.cardIconBox", etc.
Esses estilos DEVEM JÁ EXISTIR na tela Início (são os mesmos dos cards
de Cronograma/Simulados/Livros/Matérias).

Se os nomes dos estilos forem diferentes na sua tela, ajuste pra usar
os mesmos que os outros cards usam. O importante é ficar visualmente
idêntico aos cards existentes.


==============================================================
  REGISTRO DA TELA NO NAVEGADOR
==============================================================

Como você usa react-navigation (vi no simulados.tsx), você precisa
registrar a tela Questoes em algum lugar do seu Stack Navigator.

Procura o arquivo onde estão registradas as outras telas
(SimuladoAndamento, GabaritoScreen, etc) — geralmente é um
App.tsx ou navigation.tsx — e adiciona:

  <Stack.Screen name="Questoes" component={QuestoesScreen} />

E o import:

  import QuestoesScreen from './<caminho>/questoes';


==============================================================
  ONDE COLOCAR O ARQUIVO questoes.tsx
==============================================================

Coloca na MESMA pasta do simulados.tsx que você me enviou.
Provavelmente algo tipo:

  K:\nivelis005\nivelis005\Nivelis\app\(tabs)\(simulados)\questoes.tsx

(O caminho exato depende da estrutura do seu projeto.)
*/
