import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, StatusBar, ActivityIndicator, Modal
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import { auth } from '../../../../services/firebase';
import { simuladosApi, questoesApi, questoesFeitasApi, MOCK_QUESTOES, Questao, proceduralApi } from '../../../../services/apiService';
import { salvarHistorico } from '../../../../services/desempenhoService';
import CarregandoLento from '../../../../components/CarregandoLento';
import { useTheme } from '../../../TemasAcoes/Temas';
import NivelisModal, { useNivelisModal } from '../../../../components/NivelisModal';

export default function SimuladoAndamentoScreen() {
  const navigation = useNavigation<any>();
  const route      = useRoute<any>();
  const { isDarkMode } = useTheme();
  const { modal, showModal } = useNivelisModal();

  const simuladoId = route.params?.simuladoId ?? null;
  const tipoParam  = (route.params?.tipo as 'ENEM' | 'ENADE') ?? 'ENEM';
  // Vindos da tela de montagem
  const procDisciplinas = route.params?.proceduralDisciplinas as string | undefined;
  const procQuantidade  = (route.params?.proceduralQuantidade as number) ?? 30;
  const procMinutos     = (route.params?.proceduralMinutos as number) ?? 90;

  const [questoes,       setQuestoes]       = useState<Questao[]>([]);
  const [carregando,     setCarregando]     = useState(true);
  const [fonteQuestoes,  setFonteQuestoes]  = useState<'api' | 'demo'>('demo');
  const [indiceAtual,    setIndiceAtual]    = useState(0);
  const [respostas,      setRespostas]      = useState<Record<string, string>>({});
  // Começa em ZERO, não em 4h30. O 16200 fixo era chute de simulado longo:
  // um caderno de 10 questões nascia com 4h30 no relógio, e se o
  // carregamento falhasse antes do iniciarCronometro a tela mostrava esse
  // tempo inventado. Agora o cronômetro só existe depois de ser iniciado.
  const [tempoRestante,  setTempoRestante]  = useState(0);
  const [enviando,       setEnviando]       = useState(false);

  // Duração com que o cronômetro COMEÇOU. O tempo gasto era calculado
  // contra 16200 fixo, o que só valia para o simulado longo: um caderno
  // montado de 60 min já nascia com 12600 s de "tempo gasto".
  const tempoInicialRef = useRef(0);
  // Trava: a entrega automática por tempo esgotado pode ser avaliada em
  // mais de um render, e sem isto o resultado seria enviado duas vezes.
  const entregouRef = useRef(false);
  // Trava do aviso de 5 minutos — senão ele reapareceria a cada segundo.
  const avisouRef = useRef(false);
  // Mapa de questões — o que o ícone de grade do cabeçalho sempre prometeu.
  const [mapaAberto, setMapaAberto] = useState(false);

  const theme = {
    bg:          isDarkMode ? "#000000" : "#F5F5F7",
    card:        isDarkMode ? "#121214" : "#FFFFFF",
    cardSec:     isDarkMode ? "#18181B" : "#F0F0F0",
    text:        isDarkMode ? "#FFFFFF" : "#1A1A1A",
    sub:         isDarkMode ? "#A1A1AA" : "#666666",
    border:      isDarkMode ? "#27272A" : "#E5E5E5",
    primary:     "#7D53DD",
    primaryLight: isDarkMode ? "#A78BFA" : "#6B59A0",   // 2.50 → 4.5+ no claro
    danger:      "#EF4444",
  };

  // Carrega questões: simulado específico OU questões aleatórias via questoesApi
  useEffect(() => {
    (async () => {
      setCarregando(true);
      try {
        // Caderno montado pelo usuário na tela de montagem. Vem antes de
        // tudo: ele pediu ESTE conteúdo, não um simulado qualquer.
        if (procDisciplinas) {
          const sim = await proceduralApi.simulado(
            procDisciplinas, procQuantidade, tipoParam, procMinutos,
          );
          if (sim?.questoes?.length) {
            setQuestoes(sim.questoes);
            setFonteQuestoes('api');
            iniciarCronometro((sim.duracao_minutos ?? procMinutos) * 60);
          } else {
            // Sem material não dá para inventar caderno: avisa em vez de
            // servir MOCK como se fosse o que ele pediu.
            setQuestoes([]);
            setFonteQuestoes('demo');
            iniciarCronometro(procMinutos * 60);
          }
          return;
        }

        if (simuladoId) {
          // Simulado específico — busca questoes reais (Firestore → REST → /montar)
          // Passa uid pra priorizar questoes que o usuario ainda nao fez
          const uid = auth.currentUser?.uid;
          const sim = await simuladosApi.buscarPorId(simuladoId, uid);
          if (sim?.questoes?.length) {
            setQuestoes(sim.questoes);
            setFonteQuestoes('api');
            iniciarCronometro((sim.duracao_minutos ?? duracaoPara(sim.questoes.length)) * 60);
          } else {
            // Simulado sem questoes embarcadas — tenta carregar por materia
            // Extrai materia do titulo (ex: "ENEM 2022 — Humanas" → "humanas")
            const materiaSim = sim?.titulo?.split('—')?.[1]?.trim()?.toLowerCase();
            console.log('[SimuladoAndamento] Simulado vazio, tentando questoesApi com materia:', materiaSim);
            // A lista é guardada numa variável antes de ir para o estado
            // porque o cronômetro precisa do TAMANHO dela: setQuestoes é
            // assíncrono, então ler `questoes.length` logo abaixo daria o
            // valor antigo.
            let lista: Questao[];
            try {
              const qs = await questoesApi.listar({
                tipo: tipoParam,
                materia: materiaSim,
                limit: 10,
              });
              lista = qs.length ? qs : MOCK_QUESTOES;
              setFonteQuestoes(qs.length ? 'api' : 'demo');
            } catch {
              lista = MOCK_QUESTOES;
              setFonteQuestoes('demo');
            }
            setQuestoes(lista);
            iniciarCronometro((sim?.duracao_minutos ?? duracaoPara(lista.length)) * 60);
          }
        } else {
          // Início Rápido: carrega questões reais via questoesApi
          let lista: Questao[];
          try {
            const qs = await questoesApi.listar({ tipo: tipoParam, limit: 20 });
            lista = qs.length ? qs : MOCK_QUESTOES;
            setFonteQuestoes(qs.length ? 'api' : 'demo');
          } catch {
            lista = MOCK_QUESTOES;
            setFonteQuestoes('demo');
          }
          setQuestoes(lista);
          // Era 90 min fixo para qualquer quantidade. Agora acompanha o
          // caderno: 20 questões dão 1h, 3 de demonstração dão o piso.
          iniciarCronometro(duracaoPara(lista.length) * 60);
        }
      } catch {
        setQuestoes(MOCK_QUESTOES);
      } finally {
        setCarregando(false);
      }
    })();
  }, [simuladoId, procDisciplinas, procQuantidade]);

  /**
   * Quanto tempo dar a um caderno quando ninguém disse.
   *
   * Três minutos por questão, que é a conta que a tela de montagem já usa —
   * assim o mesmo caderno tem a mesma duração, venha de onde vier. O piso de
   * 10 minutos evita cronômetro ridículo num caderno de duas questões.
   *
   * O padrão antigo era 270 minutos para tudo. Um simulado de 10 questões
   * nascia com 4h30, e quem olhasse o relógio não tinha ideia de quanto a
   * prova realmente valia.
   */
  const duracaoPara = (quantidade: number) => Math.max(10, quantidade * 3);

  const iniciarCronometro = (segundos: number) => {
    tempoInicialRef.current = segundos;
    setTempoRestante(segundos);
  };

  // Cronômetro — só conta. O updater de estado tem que ser puro: foi
  // chamar o finalizar de dentro dele que congelou as respostas em {}.
  useEffect(() => {
    if (carregando || tempoInicialRef.current <= 0) return;
    const timer = setInterval(() => {
      setTempoRestante(prev => (prev <= 1 ? 0 : prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [carregando]);

  // Aviso de 5 minutos.
  //
  // O único sinal de tempo acabando era a cor do relógio virar vermelha —
  // invisível para quem não distingue cor, e fácil de não ver mesmo para
  // quem distingue, já que o relógio fica num canto e a pessoa está lendo a
  // questão. Um aviso que interrompe é o ponto: ele existe para ser notado.
  useEffect(() => {
    if (carregando || avisouRef.current) return;
    if (tempoInicialRef.current <= 360) return;   // prova curta: não cabe
    if (tempoRestante > 300 || tempoRestante <= 0) return;
    avisouRef.current = true;
    showModal(
      'Faltam 5 minutos',
      'Quando o tempo acabar, entregamos o que você já respondeu. '
      + 'As questões em branco contam como erradas.',
      'warning',
      [{ text: 'Continuar', style: 'primary', onPress: () => {} }],
    );
  }, [tempoRestante, carregando]);

  // Entrega automática, em efeito SEPARADO.
  //
  // Antes o finalizarSimulado era chamado de dentro do setInterval, cuja
  // closure ficava presa ao render em que `carregando` virou false — e
  // naquele render `respostas` ainda era {}. Quem estourasse o tempo tinha
  // a prova inteira gravada com zero acerto. Aqui o efeito roda em um
  // render novo, então lê as respostas de verdade.
  useEffect(() => {
    if (carregando || tempoInicialRef.current <= 0) return;
    if (tempoRestante > 0 || entregouRef.current) return;
    entregouRef.current = true;

    // A ORDEM aqui é deliberada: grava primeiro, avisa depois, navega só
    // quando a pessoa tocar. Antes, o tempo zerar trocava a tela sem dizer
    // nada — alguém lendo a questão 14 via o gabarito aparecer do nada e
    // não sabia por quê.
    //
    // Gravar antes do aviso é o que protege o resultado: se ela largar o
    // telefone sem tocar em nada, a prova já está salva.
    (async () => {
      const destino = await enviarRespostas(false);
      if (!destino) return;   // deu erro: enviarRespostas já avisou
      showModal(
        'Tempo esgotado',
        'Entregamos o que você respondeu até agora. '
        + 'As questões em branco contam como erradas.',
        'warning',
        [{ text: 'Ver gabarito', style: 'primary',
           onPress: () => navigation.replace('GabaritoScreen', destino) }],
      );
    })();
  }, [tempoRestante, carregando]);

  const formatarTempo = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
  };

  /** "1h30", "45min" — para dizer de quanto é a prova, não só quanto resta. */
  const emHorasMinutos = (seg: number) => {
    const min = Math.round(seg / 60);
    if (min < 60) return `${min}min`;
    const h = Math.floor(min / 60), m = min % 60;
    return m === 0 ? `${h}h` : `${h}h${String(m).padStart(2, '0')}`;
  };
  const totalLegivel  = emHorasMinutos(tempoInicialRef.current);
  const tempoAcabando = tempoInicialRef.current > 0
                     && tempoRestante <= Math.max(300, tempoInicialRef.current / 6);

  const questaoAtual = questoes[indiceAtual];
  const progresso    = questoes.length > 0 ? ((indiceAtual + 1) / questoes.length) * 100 : 0;

  // Trava para o beforeRemove: quando o próprio diálogo manda sair, a saída
  // não pode ser interceptada de novo, senão o diálogo reabre em laço.
  const saindoRef = useRef(false);

  /**
   * Confirmação de saída.
   *
   * O título dizia "Pausar Simulado?" e a ação era sair descartando tudo.
   * Pausar e descartar são coisas opostas, e o usuário lia a palavra que
   * estava em destaque — a que ele acreditava estar escolhendo não era a
   * que acontecia.
   *
   * `aoSair` existe porque o gesto de voltar precisa continuar a navegação
   * que foi interceptada, enquanto o X do cabeçalho só precisa de goBack.
   */
  const handleSair = (aoSair?: () => void) => {
    const respondidas = Object.keys(respostas).length;
    showModal(
      'Sair do simulado?',
      respondidas > 0
        ? `As ${respondidas} ${respondidas === 1 ? 'resposta' : 'respostas'} desta prova `
          + 'serão descartadas. Não dá para retomar depois.'
        : 'Não dá para retomar depois — ao voltar, o caderno é montado de novo.',
      'warning',
      [
        { text: 'Continuar prova', style: 'secondary', onPress: () => {} },
        { text: 'Sair e descartar', style: 'danger', onPress: () => {
            saindoRef.current = true;
            if (aoSair) aoSair(); else navigation.goBack();
          } },
      ],
    );
  };

  // O gesto de voltar e o botão físico do Android saíam CALADOS: a
  // confirmação só existia no X do cabeçalho, e é pelo gesto que a maioria
  // das pessoas sai de uma tela. Quem deslizasse sem querer perdia a prova.
  useEffect(() => {
    const parar = navigation.addListener('beforeRemove', (e: any) => {
      // Entrega concluída ou saída já confirmada: deixa passar.
      if (saindoRef.current || entregouRef.current || enviando) return;
      if (questoes.length === 0) return;      // nada a perder
      e.preventDefault();
      handleSair(() => navigation.dispatch(e.data.action));
    });
    return parar;
  }, [navigation, respostas, questoes.length, enviando]);

  // Só o botão de finalizar chama isto. A entrega por tempo esgotado
  // tem caminho próprio, no efeito acima.
  const finalizarSimulado = async () => {
    {
      const naoRespondidas = questoes.length - Object.keys(respostas).length;
      if (naoRespondidas > 0) {
        showModal(
          'Questões em branco',
          `Você ainda tem ${naoRespondidas} questão(ões) sem resposta. Deseja finalizar mesmo assim?`,
          'warning',
          [
            { text: 'Revisar', style: 'secondary', onPress: () => {} },
            { text: 'Finalizar', style: 'primary', onPress: () => enviarRespostas() },
          ],
        );
        return;
      }
    }
    await enviarRespostas();
  };

  const enviarRespostas = async (navegar = true) => {
    setEnviando(true);
    try {
      const uid          = auth.currentUser?.uid ?? 'anonimo';
      const acertos      = questoes.filter(q => respostas[q.id] === q.gabarito).length;
      const tempoGasto   = Math.max(0, tempoInicialRef.current - tempoRestante);
      const titulo       = route.params?.titulo ?? 'Simulado';
      const tipo         = (route.params?.tipo as 'ENEM' | 'ENADE') ?? 'ENEM';

      // Save to API (best-effort)
      if (simuladoId) {
        try {
          await simuladosApi.enviarResultado({
            simulado_id: simuladoId,
            usuario_uid: uid,
            respostas,
            acertos,
            total: questoes.length,
            tempo_segundos: tempoGasto,
          });
        } catch { /* API offline — ignore silently */ }
      }

      // Grava no acompanhamento de desempenho — MENOS o simulado de
      // demonstração. Os cards "Simulado Demo ENEM/ENADE" aparecem quando o
      // servidor está fora, e quem os explorou por curiosidade ficava com o
      // resultado somado em "Meu desempenho" para sempre, sem como desfazer.
      // Resultado de conteúdo de exemplo não é desempenho de ninguém.
      const ehDemonstracao = String(simuladoId).startsWith('mock_');
      if (ehDemonstracao) {
        console.log('[simulado] demonstração — não grava no desempenho');
      } else {
        await salvarHistorico(
          simuladoId,
          titulo,
          tipo,
          acertos,
          questoes.length,
          tempoGasto,
          respostas,
          questoes,
        );
      }

      // Marca as questoes respondidas como "feitas" no Firestore (anti-repeticao)
      // So marca as que o usuario realmente respondeu (nao as em branco)
      const idsRespondidas = questoes
        .filter(q => respostas[q.id] != null)
        .map(q => String(q.id));
      questoesFeitasApi.marcar(uid, idsRespondidas).catch(() => {});

      const destino = {
        questoes,
        respostas,
        acertos,
        total:         questoes.length,
        tempoSegundos: tempoGasto,
        titulo,
        tipo,
      };
      // Quem chamou decide se navega agora. A entrega por tempo esgotado
      // precisa gravar primeiro e navegar só depois do aviso.
      if (navegar) navigation.replace('GabaritoScreen', destino);
      return destino;
    } catch (err) {
      console.error('Erro ao enviar resultado:', err);
      showModal('Erro', 'Não foi possível salvar o resultado. Tente novamente.', 'error');
      return null;
    } finally {
      setEnviando(false);
    }
  };

  if (carregando) {
    return (
      <View style={[styles.container, { backgroundColor: theme.bg }]}>
        <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
        <CarregandoLento
          titulo="Montando seu caderno"
          tema={theme}
          onCancelar={() => navigation.goBack()}
          rotuloCancelar="Cancelar"
        />
      </View>
    );
  }

  // Sem questão nenhuma. Sem esta saída, a tela renderizava "Questão 1 de 0"
  // com o cronômetro correndo, sem botão de finalizar e sem explicação —
  // porque `indiceAtual === questoes.length - 1` vira `0 === -1`.
  if (questoes.length === 0) {
    return (
      <View style={[styles.container, { backgroundColor: theme.bg, justifyContent: 'center', alignItems: 'center', padding: 32 }]}>
        <Ionicons name="file-tray-outline" size={44} color={theme.sub} />
        <Text style={{ color: theme.text, fontSize: 17, fontWeight: '700', marginTop: 16, textAlign: 'center' }}>
          Não foi possível montar este caderno
        </Text>
        <Text style={{ color: theme.sub, marginTop: 10, textAlign: 'center', lineHeight: 21 }}>
          O servidor de questões não respondeu, ou o conteúdo escolhido não
          tem material suficiente. Tente de novo, ou escolha outro conteúdo.
        </Text>
        <TouchableOpacity accessibilityRole="button"
          onPress={() => navigation.goBack()}
          style={{
            marginTop: 24, backgroundColor: theme.primary, borderRadius: 12,
            paddingHorizontal: 28, paddingVertical: 14,
          }}
        >
          <Text style={{ color: '#FFF', fontWeight: '700' }}>Voltar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />

      {/* HEADER */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => handleSair()} style={styles.iconButton} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                          accessibilityRole="button"
                          accessibilityLabel="Sair do simulado">
          <Ionicons name="close" size={24} color={theme.text} />
        </TouchableOpacity>

        {/*
          Mostra "01:28:30 de 1h30". Sem o total, o relógio é um número sem
          régua: a pessoa não sabe se uma hora restante é folga ou aperto.
          O limiar do vermelho também deixou de ser fixo em 30 min — num
          caderno de 30 minutos ele nasceria vermelho. Agora é o último
          sexto da prova, ou 5 minutos, o que for maior.
        */}
        <View style={[styles.timerBox, { backgroundColor: theme.cardSec }]}>
          <Ionicons name="time-outline" size={16}
                    color={tempoAcabando ? theme.danger : theme.text} />
          <Text style={[styles.timerText, { color: tempoAcabando ? theme.danger : theme.text }]}
                accessibilityLabel={`Tempo restante: ${formatarTempo(tempoRestante)} de ${totalLegivel}`}>
            {formatarTempo(tempoRestante)}
          </Text>
          {tempoInicialRef.current > 0 && (
            <Text style={[styles.timerTotal, { color: theme.sub }]}>de {totalLegivel}</Text>
          )}
        </View>

        {/*
          Este botão existia sem onPress: o usuário tocava esperando o mapa
          de questões e não acontecia nada. Em prova de 45 questões,
          navegar só por Anterior/Próxima é 44 toques para chegar na
          última e conferir se ficou em branco.
        */}
        <TouchableOpacity
          style={styles.iconButton} hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
          onPress={() => setMapaAberto(true)}
          accessibilityRole="button"
          accessibilityLabel={`Mapa de questões: ${Object.keys(respostas).length} de ${questoes.length} respondidas`}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Ionicons name="grid-outline" size={20} color={theme.text} />
        </TouchableOpacity>
      </View>

      {/* BARRA DE PROGRESSO */}
      <View style={[styles.progressBg, { backgroundColor: theme.cardSec }]}>
        <View style={[styles.progressFill, { backgroundColor: theme.primary, width: `${progresso}%` }]} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        <View style={styles.questaoHeader}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Text style={[styles.materiaLabel, { color: theme.primaryLight }]}>
              {questaoAtual?.materia ?? ''}
            </Text>
            <View style={{
              backgroundColor: fonteQuestoes === 'api' ? '#10B98120' : '#F59E0B20',
              paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6,
            }}>
              <Text style={{
                fontSize: 10, fontWeight: 'bold',
                // O fundo é a mesma cor a 12%. No claro, escrever com a cor
                // cheia por cima dava 1.95:1 — o aviso de "servidor fora do
                // ar" sumia justamente quando precisava ser lido. Só o texto
                // escurece; o fundo continua o mesmo.
                color: fonteQuestoes === 'api'
                  ? (isDarkMode ? '#10B981' : '#065F46')
                  : (isDarkMode ? '#F59E0B' : '#92400E'),
              }}>
                {fonteQuestoes === 'api' ? '● Questões oficiais'
                                         : '● Exemplos — servidor fora do ar'}
              </Text>
            </View>
          </View>
          <Text style={[styles.contador, { color: theme.sub }]}>
            Questão {indiceAtual + 1} de {questoes.length}
          </Text>
        </View>

        <Text style={[styles.enunciado, { color: theme.text }]}>
          {questaoAtual?.enunciado ?? ''}
        </Text>

        <View style={styles.alternativas}>
          {(questaoAtual?.alternativas ?? []).map(alt => {
            const selecionada = respostas[questaoAtual.id] === alt.id;
            return (
              <TouchableOpacity accessibilityRole="button"
                key={alt.id}
                activeOpacity={0.7}
                onPress={() => setRespostas({ ...respostas, [questaoAtual.id]: alt.id })}
                style={[
                  styles.altCard,
                  {
                    backgroundColor: selecionada ? theme.primary + '18' : theme.card,
                    borderColor:     selecionada ? theme.primary : theme.border,
                  },
                ]}
              >
                <View style={[
                  styles.altLetra,
                  {
                    backgroundColor: selecionada ? theme.primary : theme.cardSec,
                    borderColor:     selecionada ? theme.primary : theme.border,
                  },
                ]}>
                  <Text style={[styles.altLetraText, { color: selecionada ? '#FFF' : theme.sub }]}>
                    {alt.id}
                  </Text>
                </View>
                <Text style={[styles.altTexto, { color: theme.text }]}>{alt.texto}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </ScrollView>

      {/* RODAPÉ */}
      <View style={[styles.footer, { backgroundColor: theme.card, borderTopColor: theme.border }]}>
        <TouchableOpacity accessibilityRole="button"
          style={[styles.navBtn, indiceAtual === 0 && { opacity: 0.3 }]}
          onPress={() => setIndiceAtual(i => i - 1)}
          disabled={indiceAtual === 0}
        >
          <Ionicons name="chevron-back" size={20} color={theme.text} />
          <Text style={[styles.navBtnText, { color: theme.text }]}>Anterior</Text>
        </TouchableOpacity>

        {indiceAtual === questoes.length - 1 ? (
          <TouchableOpacity accessibilityRole="button"
            style={[styles.btnFinalizar, { backgroundColor: theme.primary }, enviando && { opacity: 0.7 }]}
            onPress={() => finalizarSimulado()}
            disabled={enviando}
          >
            {enviando
              ? <ActivityIndicator color="#FFF" size="small" />
              : <>
                  <Text style={styles.btnFinalizarText}>Finalizar</Text>
                  <Ionicons name="checkmark" size={18} color="#FFF" />
                </>
            }
          </TouchableOpacity>
        ) : (
          <TouchableOpacity accessibilityRole="button"
            style={[styles.navBtn, { backgroundColor: theme.cardSec, borderRadius: 8, paddingHorizontal: 16 }]}
            onPress={() => setIndiceAtual(i => i + 1)}
          >
            <Text style={[styles.navBtnText, { color: theme.text }]}>Próxima</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.text} />
          </TouchableOpacity>
        )}
      </View>

      {/* ── MAPA DE QUESTÕES ──────────────────────────────────────────── */}
      <Modal visible={mapaAberto} transparent animationType="fade"
             onRequestClose={() => setMapaAberto(false)}>
        <TouchableOpacity style={estilosMapa.fundo} activeOpacity={1}
                          onPress={() => setMapaAberto(false)}>
          <TouchableOpacity activeOpacity={1}
                            style={[estilosMapa.caixa, { backgroundColor: theme.card }]}>
            <Text style={[estilosMapa.titulo, { color: theme.text }]}>Questões</Text>
            <Text style={[estilosMapa.resumo, { color: theme.sub }]}>
              {Object.keys(respostas).length} de {questoes.length} respondidas
            </Text>

            <ScrollView style={{ maxHeight: 300 }} contentContainerStyle={estilosMapa.grade}>
              {questoes.map((q, i) => {
                const respondida = respostas[q.id] != null;
                const atual      = i === indiceAtual;
                return (
                  <TouchableOpacity
                    key={String(q.id)}
                    onPress={() => { setIndiceAtual(i); setMapaAberto(false); }}
                    accessibilityRole="button"
                    accessibilityLabel={
                      `Questão ${i + 1}${respondida ? ', respondida' : ', em branco'}`
                      + `${atual ? ', atual' : ''}`}
                    style={[
                      estilosMapa.celula,
                      { borderColor: atual ? theme.primary : theme.border,
                        borderWidth: atual ? 2 : 1,
                        // Respondida tem FUNDO cheio, em branco fica vazia.
                        // A diferença é de forma, não só de cor: quem não
                        // distingue as duas cores ainda vê cheio contra vazio.
                        backgroundColor: respondida ? theme.primary + '28' : 'transparent' },
                    ]}
                  >
                    <Text style={[estilosMapa.numero,
                                  { color: respondida ? theme.primary : theme.sub,
                                    fontWeight: atual ? '800' : '600' }]}>
                      {i + 1}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>

            <View style={estilosMapa.legenda}>
              <View style={[estilosMapa.amostra, { backgroundColor: theme.primary + '28', borderColor: theme.border }]} />
              <Text style={[estilosMapa.legendaTxt, { color: theme.sub }]}>respondida</Text>
              <View style={[estilosMapa.amostra, { backgroundColor: 'transparent', borderColor: theme.border }]} />
              <Text style={[estilosMapa.legendaTxt, { color: theme.sub }]}>em branco</Text>
            </View>

            <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
              style={[estilosMapa.fechar, { borderColor: theme.border }]}
              onPress={() => setMapaAberto(false)}
              accessibilityRole="button" accessibilityLabel="Fechar o mapa"
            >
              <Text style={[estilosMapa.fecharTxt, { color: theme.text }]}>Fechar</Text>
            </TouchableOpacity>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>

      <NivelisModal {...modal} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingTop: 50, paddingBottom: 15, paddingHorizontal: 20, borderBottomWidth: 1,
  },
  iconButton: { padding: 5 },
  timerBox:   { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  timerTotal: { fontSize: 10.5, marginLeft: 3, opacity: 0.85 },
  timerText:  { fontSize: 14, fontWeight: 'bold', marginLeft: 6, fontVariant: ['tabular-nums'] },
  progressBg: { height: 4, width: '100%' },
  progressFill: { height: '100%' },
  scroll:      { padding: 20, paddingBottom: 110 },
  questaoHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  materiaLabel:  { fontSize: 12, fontWeight: 'bold', letterSpacing: 1 },
  contador:      { fontSize: 13, fontWeight: 'bold' },
  enunciado:     { fontSize: 16, lineHeight: 26, marginBottom: 30 },
  alternativas:  { gap: 12 },
  altCard:  { flexDirection: 'row', alignItems: 'center', padding: 16, borderRadius: 12, borderWidth: 1 },
  altLetra: { width: 32, height: 32, borderRadius: 16, borderWidth: 1, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  altLetraText: { fontSize: 14, fontWeight: 'bold' },
  altTexto:     { flex: 1, fontSize: 15, lineHeight: 22 },
  footer: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, paddingBottom: 30, borderTopWidth: 1,
    position: 'absolute', bottom: 0, width: '100%',
  },
  navBtn:         { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingHorizontal: 10 },
  navBtnText:     { fontSize: 16, fontWeight: '500', marginHorizontal: 4 },
  btnFinalizar:   { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 24, borderRadius: 8, gap: 8 },
  btnFinalizarText: { color: '#FFF', fontSize: 16, fontWeight: 'bold' },
});
// ── Estilos do mapa de questões ──────────────────────────────────────────────
const estilosMapa = StyleSheet.create({
  fundo: {
    flex: 1, backgroundColor: 'rgba(0,0,0,0.55)',
    justifyContent: 'center', alignItems: 'center', padding: 24,
  },
  caixa: {
    width: '100%', maxWidth: 360, borderRadius: 18, padding: 20,
  },
  titulo: { fontSize: 17, fontWeight: '700', textAlign: 'center' },
  resumo: { fontSize: 13, textAlign: 'center', marginTop: 4, marginBottom: 16 },
  grade: {
    flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'center',
    paddingBottom: 4,
  },
  celula: {
    // 44x44: o mínimo recomendado para alvo de toque. Cabem 6 por linha
    // numa tela de 390, com folga para o espaçamento.
    width: 44, height: 44, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
  },
  numero: { fontSize: 14, fontVariant: ['tabular-nums'] },
  legenda: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, marginTop: 16, flexWrap: 'wrap',
  },
  amostra: { width: 14, height: 14, borderRadius: 4, borderWidth: 1 },
  legendaTxt: { fontSize: 11.5, marginRight: 8 },
  fechar: {
    marginTop: 16, paddingVertical: 11, borderRadius: 10, borderWidth: 1,
    alignItems: 'center',
  },
  fecharTxt: { fontSize: 14, fontWeight: '600' },
});
