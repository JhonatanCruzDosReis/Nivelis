import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, StatusBar, ActivityIndicator, Dimensions, Platform,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect, useRoute } from '@react-navigation/native';
import { auth } from '../../../../services/firebase';
import { questoesApi, questoesFeitasApi, MOCK_QUESTOES, Questao, proceduralApi } from '../../../../services/apiService';
import { listar as listarMinhas, ehQuestaoPropria } from '../../../../services/minhasQuestoesService';
import {
  salvarSessaoQuestoes, carregarSessoesQuestoes, carregarStatsQuestoes,
  SessaoQuestoes, QuestoesStats, formatarDataQuestoes,
} from '../../../../services/questoesService';
import { useTheme } from '../../../TemasAcoes/Temas';
import NivelisModal, { useNivelisModal } from '../../../../components/NivelisModal';

const QUESTOES_POR_SESSAO = 15;
type Aba = 'Praticar' | 'Histórico';
type Modo = 'novas' | 'refazer';

const { height } = Dimensions.get('window');

// Matérias por tipo (chips de filtro)
const MATERIAS: Record<'ENEM' | 'ENADE', string[]> = {
  ENEM:  ['Todas', 'Matemática', 'Linguagens', 'Humanas', 'Natureza'],
  ENADE: ['Todas', 'Redes de Computadores', 'Análise e Desenvolvimento de Sistemas', 'Direito', 'Administração'],
};

export default function QuestoesScreen() {
  const navigation = useNavigation<any>();
  const route      = useRoute<any>();
  const { isDarkMode } = useTheme();
  const { modal, showModal } = useNivelisModal();

  // Vindos da tela de montagem: o usuário escolheu ESTE conteúdo.
  // Um toque nos filtros desliga o pedido que veio da montagem: senão os
  // chips de matéria ficariam inertes, porque o efeito sempre refaria a
  // busca procedural e ignoraria a escolha nova.
  const [ignorarParam, setIgnorarParam] = useState(false);
  const procDisciplina = ignorarParam
    ? undefined
    : (route.params?.proceduralDisciplina as string | undefined);
  const procTopico     = route.params?.proceduralTopico as string | undefined;
  const procQuantidade = (route.params?.proceduralQuantidade as number) ?? QUESTOES_POR_SESSAO;

  const [aba, setAba]           = useState<Aba>('Praticar');
  const [tipo, setTipo]         = useState<'ENEM' | 'ENADE'>(route.params?.tipo ?? 'ENEM');
  const [materia, setMateria]   = useState('Todas');

  // Praticar
  const [questoes, setQuestoes]               = useState<Questao[]>([]);
  const [carregando, setCarregando]           = useState(true);
  const [fonteQuestoes, setFonteQuestoes]     = useState<'api' | 'demo' | 'minhas'>('demo');
  const [respostas, setRespostas]             = useState<Record<string, string>>({});
  const [confirmadas, setConfirmadas]         = useState<Record<string, boolean>>({});
  const [finalizada, setFinalizada]           = useState(false);

  // Praticar inéditas, ou revisar o que já foi feito. Refazer é sempre um
  // pedido explícito: o modo 'novas' nunca devolve questão respondida.
  const [modo, setModo] = useState<Modo>('novas');
  // Quantas feitas existem no banco desta matéria — decide se a oferta de
  // refazer aparece. Zero significa que não há o que revisar.
  const [feitasDisponiveis, setFeitasDisponiveis] = useState(0);
  // De onde vieram as questões da sessão atual, para a linha de rodapé e para
  // os avisos de degradação (repetida por falta de opção, ou cache offline).
  const [origem, setOrigem] = useState<{
    banco: number; geradas: number; repetidas: number; doCache: boolean;
  }>({ banco: 0, geradas: 0, repetidas: 0, doCache: false });
  // Muda só para forçar o efeito a rodar de novo ("Nova Sessão").
  const [recarga, setRecarga] = useState(0);

  // Histórico
  const [sessoes, setSessoes]   = useState<SessaoQuestoes[]>([]);
  const [stats, setStats]       = useState<QuestoesStats | null>(null);
  const [carregandoHist, setCarregandoHist] = useState(false);

  const theme = {
    bg:        isDarkMode ? "#000000" : "#F5F5F7",
    card:      isDarkMode ? "#121214" : "#FFFFFF",
    cardSec:   isDarkMode ? "#18181B" : "#F0F0F0",
    text:      isDarkMode ? "#FFFFFF" : "#1A1A1A",
    sub:       isDarkMode ? "#A1A1AA" : "#666666",
    border:    isDarkMode ? "#27272A" : "#E5E5E5",
    // O rosa é FUNDO de botão com texto branco: em #EC4899 isso dava
    // 3.53:1. Escurecido 16%, o branco por cima passa a 4.81:1.
    primary:   "#C63C81",  // rosa (cor do card Questões)
    primaryLt: "#F472B6",
    success:   "#10B981",
    danger:    "#EF4444",
    warning:   "#F59E0B",

    // ── as mesmas cores, em versão LEGÍVEL sobre o próprio tom ──
    //
    // O padrão do app é pintar o fundo do selo com a cor a 12% ("+20") e
    // escrever por cima com a cor cheia. No escuro funciona: a cor clara
    // sobre o tom escurecido dá 7:1. No CLARO não funciona — a cor cheia
    // sobre o próprio tom claro dá 1.95:1, e o aviso "servidor fora do ar"
    // ficava praticamente invisível justamente quando mais importa ser lido.
    //
    // Então o fundo continua igual e só o TEXTO muda de tom no claro.
    warningTxt: isDarkMode ? "#F59E0B" : "#92400E",   // 1.95 → 6.45
    successTxt: isDarkMode ? "#10B981" : "#065F46",   // 2.25 → 6.82
    dangerTxt:  isDarkMode ? "#EF4444" : "#991B1B",
    primaryTxt: isDarkMode ? "#EC4899" : "#9D174D",   // 3.02 → 6.76
  };

  /**
   * O MESMO uid para ler e para gravar.
   *
   * Antes a leitura usava `auth.currentUser?.uid` (podia ser undefined) e a
   * gravação `?? 'anonimo'`. Deslogado, isso desligava a anti-repetição por
   * inteiro: a leitura não filtrava nada e a gravação era descartada. Agora
   * 'anonimo' é um uid válido no aparelho — só não sincroniza com a nuvem.
   */
  const uidAtual = () => auth.currentUser?.uid ?? 'anonimo';

  // ── GUARDA DE SESSÃO EM ANDAMENTO ─────────────────────────────────────────
  //
  // O efeito de carregar depende de [tipo, materia, modo] e começa limpando
  // as respostas. Então tocar num chip de matéria apagava 12 questões
  // respondidas sem avisar, e nada tinha sido salvo: o salvarSessaoQuestoes
  // só roda no finalizar.
  //
  // Agora toda troca passa por aqui. Se houver resposta confirmada e a sessão
  // não tiver sido finalizada, pergunta antes — com a opção de SALVAR, que é
  // o que o usuário quase sempre quer e que antes não existia.
  const temTrabalhoAberto = () =>
    !finalizada && Object.keys(confirmadas).length > 0;

  /** Grava a sessão no histórico e marca as questões como feitas. */
  const salvarSessao = async () => {
    await salvarSessaoQuestoes(tipo, materia, questoes, respostas);
    const ids = questoes.filter(q => respostas[q.id] != null).map(q => String(q.id));
    try { await questoesFeitasApi.marcar(uidAtual(), ids); }
    catch (e) { console.warn('[questoes] marcar feitas:', e); }
    return ids;
  };

  /**
   * Executa `trocar` — mas só depois de resolver o que fazer com o que já
   * foi respondido.
   */
  const comGuarda = (trocar: () => void) => {
    if (!temTrabalhoAberto()) { trocar(); return; }
    const n = Object.keys(confirmadas).length;
    showModal(
      'Sessão em andamento',
      `Você tem ${n} ${n === 1 ? 'questão respondida' : 'questões respondidas'} aqui. `
      + 'Sair desta lista vai descartá-las.',
      'warning',
      [
        { text: 'Cancelar', style: 'secondary', onPress: () => {} },
        { text: 'Descartar', style: 'danger',   onPress: () => trocar() },
        // 'Salvar' e não 'Salvar e sair': com três botões lado a lado num
        // aparelho de 390px, o rótulo mais longo quebrava em duas linhas e
        // desalinhava a fileira inteira. Verificado renderizando de verdade.
        { text: 'Salvar', style: 'primary', onPress: () => {
            salvarSessao()
              .catch(e => console.warn('[questoes] salvar antes de trocar:', e))
              .finally(() => trocar());
          } },
      ],
    );
  };

  // ── CARREGA QUESTÕES (Praticar) ───────────────────────────────────────────
  useEffect(() => {
    if (aba !== 'Praticar') return;
    let ativo = true;

    (async () => {
      setCarregando(true);
      setRespostas({});
      setConfirmadas({});
      setFinalizada(false);

      try {
        // Pedido explícito da montagem: gera exatamente o que foi escolhido,
        // sem passar pela cascata (que decidiria a matéria por conta própria).
        if (procDisciplina) {
          const qs = await proceduralApi.questoes(procDisciplina, procQuantidade, tipo, procTopico);
          if (!ativo) return;
          if (qs.length > 0) {
            setQuestoes(qs);
            setFonteQuestoes('api');
            return;
          }
        }

        // listarSessao: banco inédito primeiro; se faltar para fechar as 15,
        // o procedural gera a diferença. Questão já respondida não volta
        // sozinha — só pelo modo 'refazer', que é escolha do usuário.
        const sessao = await questoesApi.listarSessao({
          tipo,
          materia: materia === 'Todas' ? undefined : materia,
          limit: QUESTOES_POR_SESSAO,
          uid: uidAtual(),
          modo,
        });
        const qs = sessao.questoes;

        // As questões escritas pelo usuário entram na frente: são as que
        // ele quis guardar, e não custam requisição nenhuma.
        const minhas = modo === 'refazer' ? [] : await listarMinhas({
          tipo,
          materia: materia === 'Todas' ? undefined : materia,
        });

        if (!ativo) return;
        setFeitasDisponiveis(sessao.feitas);
        setOrigem({
          banco:     sessao.doBanco,
          geradas:   sessao.geradas,
          repetidas: sessao.repetidas,
          doCache:   sessao.doCache,
        });

        if (qs.length > 0 || minhas.length > 0) {
          setQuestoes([...minhas, ...qs].slice(0, QUESTOES_POR_SESSAO));
          setFonteQuestoes(qs.length > 0 ? 'api' : 'minhas');
        } else if (modo === 'refazer') {
          setQuestoes([]);
          setFonteQuestoes('api');
        } else {
          setQuestoes(MOCK_QUESTOES.filter((q: Questao) => q.tipo === tipo));
          setFonteQuestoes('demo');
        }
      } catch {
        if (!ativo) return;
        // Mesmo com a API fora, o que é do usuário continua acessível.
        try {
          const minhas = await listarMinhas({
            tipo,
            materia: materia === 'Todas' ? undefined : materia,
          });
          if (!ativo) return;
          if (minhas.length > 0) {
            setQuestoes(minhas.slice(0, QUESTOES_POR_SESSAO));
            setFonteQuestoes('minhas');
            return;
          }
        } catch {}
        setQuestoes(MOCK_QUESTOES.filter((q: Questao) => q.tipo === tipo));
        setFonteQuestoes('demo');
      } finally {
        if (ativo) setCarregando(false);
      }
    })();

    return () => { ativo = false; };
    // `aba` FORA das dependências de propósito: com ela aqui, ir ao Histórico
    // e voltar remontava a sessão e apagava o que estava respondido. O guard
    // `aba !== 'Praticar'` no topo continua valendo, porque o efeito lê o
    // valor atual sempre que uma das dependências reais muda.
  }, [tipo, materia, procDisciplina, procTopico, procQuantidade, modo, recarga]);

  // ── CARREGA HISTÓRICO ─────────────────────────────────────────────────────
  useFocusEffect(
    useCallback(() => {
      if (aba !== 'Histórico') return;
      let ativo = true;
      (async () => {
        setCarregandoHist(true);
        try {
          const [s, st] = await Promise.all([
            carregarSessoesQuestoes(),
            carregarStatsQuestoes(),
          ]);
          if (ativo) { setSessoes(s); setStats(st); }
        } catch {}
        if (ativo) setCarregandoHist(false);
      })();
      return () => { ativo = false; };
    }, [aba]),
  );

  // ── AÇÕES ─────────────────────────────────────────────────────────────────

  const selecionar = (qId: string, altId: string) => {
    if (confirmadas[qId]) return; // já confirmou, trava
    setRespostas(prev => ({ ...prev, [qId]: altId }));
  };

  const confirmar = (qId: string) => {
    if (!respostas[qId]) return;
    setConfirmadas(prev => ({ ...prev, [qId]: true }));
  };

  const finalizar = async () => {
    setFinalizada(true);
    // salvarSessao grava o histórico (TODAS as respondidas, inclusive geradas
    // e próprias — a contagem de acertos depende disso) e marca as feitas.
    // Aguardado, e não solto com .catch(() => {}): a gravação local é o que
    // garante que a questão não volte, e ela terminar antes do usuário sair
    // da tela é o que faz a garantia valer.
    const ids = await salvarSessao();

    // A oferta de refazer cresceu — reflete sem precisar recarregar a tela.
    setFeitasDisponiveis(n => n + ids.filter(
      id => !id.startsWith('proc-') && !id.startsWith('minha:')
         && !id.startsWith('mock_')).length);
  };

  /** Troca entre praticar inéditas e revisar as já feitas. */
  const alternarModo = (novo: Modo) => comGuarda(() => {
    if (novo === modo) { setRecarga(r => r + 1); return; }
    setModo(novo);
  });

  // Contadores da sessão atual
  const respondidas = Object.keys(confirmadas).length;
  const acertos = questoes.filter(q =>
    confirmadas[q.id] && respostas[q.id]?.toUpperCase() === String(q.gabarito ?? '').toUpperCase()
  ).length;

  // Wrapper de scroll: no web usa div nativo; no mobile usa ScrollView
  const ScrollWrapper = ({ children }: { children: React.ReactNode }) => {
    if (Platform.OS === 'web') {
      return (
        <div style={{ height: height - 180, overflowY: 'auto', overflowX: 'hidden', paddingLeft: 16, paddingRight: 16, paddingBottom: 40 }}>
          {children}
        </div>
      );
    }
    return (
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={true}>
        {children}
      </ScrollView>
    );
  };

  // ── RENDER ────────────────────────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />

      {/* HEADER */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.iconBtn} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Questões</Text>
        {/* Atalho para o banco pessoal — criar e excluir questões próprias */}
        <TouchableOpacity accessibilityRole="button"
          onPress={() => navigation.navigate('MinhasQuestoes')}
          style={styles.iconBtn} hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          accessibilityLabel="Minhas questões"
        >
          <Ionicons name="create-outline" size={23} color={theme.primary} />
        </TouchableOpacity>
      </View>

      {/* ABAS Praticar | Histórico */}
      <View style={[styles.abaContainer, { backgroundColor: theme.card }]}>
        {(['Praticar', 'Histórico'] as Aba[]).map(a => (
          <TouchableOpacity accessibilityRole="button"
            key={a}
            style={[styles.abaBtn, aba === a && { backgroundColor: theme.primary }]}
            onPress={() => { if (a === aba) return; comGuarda(() => setAba(a)); }}
          >
            <Text style={[styles.abaText, { color: aba === a ? '#FFF' : theme.sub }]}>{a}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* ============ ABA PRATICAR ============ */}
      {aba === 'Praticar' && (
        <ScrollWrapper>
          {/* Tipo ENEM/ENADE */}
          <View style={styles.tipoRow}>
            {(['ENEM', 'ENADE'] as const).map(t => (
              <TouchableOpacity accessibilityRole="button"
                key={t}
                style={[
                  styles.tipoBtn,
                  { borderColor: tipo === t ? theme.primary : theme.border },
                  tipo === t && { backgroundColor: theme.primary + '15' },
                ]}
                onPress={() => { if (t === tipo) { setIgnorarParam(true); return; }
                                 comGuarda(() => { setTipo(t); setIgnorarParam(true); }); }}
              >
                <Text style={[styles.tipoText, { color: tipo === t ? theme.primary : theme.sub }]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Chips de matéria */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsRow} contentContainerStyle={{ paddingRight: 16 }}>
            {MATERIAS[tipo].map(m => (
              <TouchableOpacity accessibilityRole="button"
                key={m}
                style={[
                  styles.chip,
                  { backgroundColor: materia === m ? theme.primary + '20' : theme.card, borderColor: materia === m ? theme.primary : theme.border },
                ]}
                onPress={() => { if (m === materia) { setIgnorarParam(true); return; }
                                 comGuarda(() => { setMateria(m); setIgnorarParam(true); }); }}
              >
                <Text style={[styles.chipText, { color: materia === m ? theme.primary : theme.sub }]} numberOfLines={1}>
                  {m}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Badge fonte + contador */}
          <View style={styles.statusRow}>
            <View style={[styles.badge, { backgroundColor: fonteQuestoes === 'api' ? theme.success + '20' : theme.warning + '20' }]}>
              <Text style={[styles.badgeText, { color: fonteQuestoes === 'api' ? theme.successTxt : theme.warningTxt }]}>
                {/* "Banco" e "Demo" eram o nosso vocabulário, não o do usuário.
                    Pior: "Demo" aparece quando o servidor falhou, e quem
                    escolheu Direito e recebeu uma questão de Camões não tinha
                    como saber disso. O rótulo agora diz o que houve. */}
                {fonteQuestoes === 'api'    ? '● Questões oficiais'
                 : fonteQuestoes === 'minhas' ? '● Suas questões'
                 : '● Exemplos — servidor fora do ar'}
              </Text>
            </View>
            {respondidas > 0 && (
              <Text style={[styles.contadorText, { color: theme.sub }]}>
                {acertos} acertos / {respondidas} respondidas
              </Text>
            )}
          </View>

          {/* Modo refazer: fica explícito que a repetição é intencional */}
          {modo === 'refazer' && !carregando && (
            <View style={[styles.faixaModo, { backgroundColor: theme.warning + '18', borderColor: theme.warning }]}>
              <MaterialCommunityIcons name="history" size={18} color={theme.warningTxt} />
              <Text style={[styles.faixaModoTxt, { color: theme.text }]}>
                Revisando questões que você já fez
              </Text>
              <TouchableOpacity accessibilityRole="button" onPress={() => alternarModo('novas')}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
                <Text style={[styles.faixaModoLink, { color: theme.primaryTxt }]}>sair</Text>
              </TouchableOpacity>
            </View>
          )}

          {/*
            Degradou: repetiu porque não havia alternativa. O usuário precisa
            saber disso — repetição silenciosa é justamente o defeito que a
            anti-repetição existe para evitar. Dizer "não conseguimos buscar
            novas" transforma um app aparentemente quebrado numa situação que
            ele entende e sabe quando tentar de novo.
          */}
          {modo === 'novas' && !carregando && origem.repetidas > 0 && (
            <View style={[styles.faixaModo, { backgroundColor: theme.warning + '18', borderColor: theme.warning }]}>
              <MaterialCommunityIcons name="wifi-off" size={18} color={theme.warningTxt} />
              <Text style={[styles.faixaModoTxt, { color: theme.text }]}>
                Não conseguimos buscar questões novas agora. Estas você já fez.
              </Text>
              <TouchableOpacity accessibilityRole="button" onPress={() => setRecarga(r => r + 1)}
                hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
                <Text style={[styles.faixaModoLink, { color: theme.primaryTxt }]}>tentar</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Veio do que o aparelho guardou: sem rede, mas com questão real */}
          {!carregando && origem.doCache && origem.repetidas === 0 && (
            <View style={[styles.faixaModo, { backgroundColor: theme.cardSec, borderColor: theme.border }]}>
              <MaterialCommunityIcons name="cloud-off-outline" size={18} color={theme.sub} />
              <Text style={[styles.faixaModoTxt, { color: theme.sub }]}>
                Você está sem conexão. Praticando com o que ficou salvo no aparelho.
              </Text>
            </View>
          )}

          {/* Oferta de revisão, sem precisar terminar a sessão primeiro */}
          {modo === 'novas' && !carregando && origem.repetidas === 0 && feitasDisponiveis > 0 && (
            <TouchableOpacity accessibilityRole="button"
              style={[styles.linhaRefazer, { borderColor: theme.border }]}
              onPress={() => alternarModo('refazer')}
            >
              <MaterialCommunityIcons name="history" size={16} color={theme.sub} />
              <Text style={[styles.linhaRefazerTxt, { color: theme.sub }]}>
                Você já fez {feitasDisponiveis} desta matéria. Refazer?
              </Text>
            </TouchableOpacity>
          )}

          {/* Lista de questões */}
          {carregando ? (
            <ActivityIndicator size="large" color={theme.primary} style={{ marginTop: 40 }} />
          ) : questoes.length === 0 ? (
            <View style={[styles.emptyBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <MaterialCommunityIcons
                name={modo === 'refazer' ? 'history' : 'help-circle-outline'}
                size={48} color={theme.sub} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>
                {modo === 'refazer' ? 'Nada para revisar ainda' : 'Sem questões aqui ainda'}
              </Text>
              {/*
                O texto antigo mandava o usuário "verificar se a API está no
                ar". Ninguém que baixou um app de estudos sabe o que é isso,
                nem tem como verificar. Diz o que aconteceu e dá o botão.
              */}
              <Text style={[styles.emptySub, { color: theme.sub }]}>
                {modo === 'refazer'
                  ? 'Você ainda não respondeu nenhuma questão desta matéria.'
                  : `Não conseguimos buscar questões de ${materia === 'Todas' ? 'nenhuma matéria' : materia} agora. `
                    + 'Pode ser a sua conexão.'}
              </Text>
              {modo === 'refazer' ? (
                <TouchableOpacity accessibilityRole="button"
                  style={[styles.btnRefazer, { borderColor: theme.border, marginTop: 14 }]}
                  onPress={() => alternarModo('novas')}
                >
                  <Text style={[styles.btnRefazerTxt, { color: theme.primary }]}>
                    Voltar às inéditas
                  </Text>
                </TouchableOpacity>
              ) : (
                <TouchableOpacity accessibilityRole="button"
                  style={[styles.btnIrPraticar, { backgroundColor: theme.primary, marginTop: 16 }]}
                  onPress={() => setRecarga(r => r + 1)}
                >
                  <Text style={styles.btnIrPraticarTxt}>Tentar novamente</Text>
                </TouchableOpacity>
              )}
            </View>
          ) : (
            <>
              {questoes.map((q, i) => {
                const minhaResp  = respostas[q.id];
                const confirmou  = confirmadas[q.id];
                const gabarito   = String(q.gabarito ?? '').toUpperCase();

                return (
                  <View key={String(q.id) ?? i} style={[styles.qCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                    {/* Cabeçalho da questão */}
                    <View style={styles.qHeader}>
                      <Text style={[styles.qNumero, { color: theme.primary }]}>Questão {i + 1}</Text>
                      <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                        {/* Marca as escritas pelo próprio usuário, para ele
                            saber que está revisando material dele. */}
                        {ehQuestaoPropria(q) && (
                          <View style={{
                            backgroundColor: `${theme.primary}22`, borderRadius: 6,
                            paddingHorizontal: 6, paddingVertical: 2, marginRight: 6,
                          }}>
                            <Text style={{ color: theme.primary, fontSize: 10, fontWeight: '700' }}>
                              MINHA
                            </Text>
                          </View>
                        )}
                        <Text style={[styles.qMateria, { color: theme.sub }]}>{q.materia ?? 'Geral'}</Text>
                      </View>
                    </View>

                    {/* Contexto (se houver) */}
                    {(q as any).contexto ? (
                      <Text style={[styles.qContexto, { color: theme.sub }]}>{(q as any).contexto}</Text>
                    ) : null}

                    {/* Enunciado */}
                    <Text style={[styles.qEnunciado, { color: theme.text }]}>{q.enunciado}</Text>

                    {/* Alternativas */}
                    <View style={styles.alts}>
                      {(q.alternativas ?? []).map(alt => {
                        const selecionada = minhaResp === alt.id;
                        const ehGabarito  = alt.id.toUpperCase() === gabarito;

                        // Cores após confirmar
                        let bgColor = theme.card;
                        let bdColor = theme.border;
                        if (confirmou) {
                          if (ehGabarito) { bgColor = theme.success + '18'; bdColor = theme.success; }
                          else if (selecionada) { bgColor = theme.danger + '18'; bdColor = theme.danger; }
                        } else if (selecionada) {
                          bgColor = theme.primary + '15'; bdColor = theme.primary;
                        }

                        return (
                          <TouchableOpacity accessibilityRole="button"
                            key={alt.id}
                            activeOpacity={confirmou ? 1 : 0.7}
                            onPress={() => selecionar(q.id, alt.id)}
                            style={[styles.alt, { backgroundColor: bgColor, borderColor: bdColor }]}
                          >
                            <View style={[styles.altLetra, { backgroundColor: selecionada || (confirmou && ehGabarito) ? bdColor : theme.cardSec, borderColor: bdColor }]}>
                              <Text style={[styles.altLetraTxt, { color: selecionada || (confirmou && ehGabarito) ? '#FFF' : theme.sub }]}>{alt.id}</Text>
                            </View>
                            <Text style={[styles.altTxt, { color: theme.text }]}>{alt.texto}</Text>
                            {confirmou && ehGabarito && (
                              <Ionicons name="checkmark-circle" size={20} color={theme.success} />
                            )}
                            {confirmou && selecionada && !ehGabarito && (
                              <Ionicons name="close-circle" size={20} color={theme.danger} />
                            )}
                          </TouchableOpacity>
                        );
                      })}
                    </View>

                    {/* Botão confirmar OU gabarito explicativo */}
                    {!confirmou ? (
                      <TouchableOpacity accessibilityRole="button"
                        style={[styles.btnConfirmar, { backgroundColor: minhaResp ? theme.primary : theme.cardSec }]}
                        onPress={() => confirmar(q.id)}
                        disabled={!minhaResp}
                      >
                        <Text style={[styles.btnConfirmarTxt, { color: minhaResp ? '#FFF' : theme.sub }]}>Confirmar</Text>
                      </TouchableOpacity>
                    ) : (
                      <View style={[styles.gabaritoBox, { backgroundColor: theme.cardSec }]}>
                        <Text style={[styles.gabaritoTitulo, { color: theme.text }]}>
                          {minhaResp?.toUpperCase() === gabarito ? '✓ Você acertou!' : `✗ Resposta correta: ${gabarito}`}
                        </Text>
                        {(q as any).explicacao ? (
                          <Text style={[styles.gabaritoTexto, { color: theme.sub }]}>{(q as any).explicacao}</Text>
                        ) : null}
                      </View>
                    )}
                  </View>
                );
              })}

              {/* Botão Finalizar sessão */}
              {/* De onde veio cada questão. Importa porque a gerada não é
                  salva no banco e não entra na memória de feitas — então ela
                  pode reaparecer como instância nova, e isso é esperado. */}
              {modo === 'novas' && origem.repetidas === 0 && (
                <Text style={[styles.linhaOrigem, { color: theme.sub }]}>
                  {origem.geradas > 0 && origem.banco > 0
                    ? `${origem.banco} do banco + ${origem.geradas} geradas na hora`
                    : origem.geradas > 0
                      ? `${origem.geradas} geradas na hora — o banco não tinha inéditas`
                      : questoes.length < QUESTOES_POR_SESSAO
                        // Sessão curta precisa de explicação: sem ela parece
                        // que o app entregou menos do que devia por defeito.
                        ? `${questoes.length} questões — era o que havia de inédito aqui`
                        : ''}
                </Text>
              )}

              {!finalizada ? (
                <TouchableOpacity accessibilityRole="button"
                  style={[styles.btnFinalizar, { backgroundColor: respondidas > 0 ? theme.primary : theme.cardSec }]}
                  onPress={finalizar}
                  disabled={respondidas === 0}
                >
                  <MaterialCommunityIcons name="content-save-check-outline" size={20} color={respondidas > 0 ? '#FFF' : theme.sub} />
                  <Text style={[styles.btnFinalizarTxt, { color: respondidas > 0 ? '#FFF' : theme.sub }]}>
                    Finalizar e Salvar ({respondidas})
                  </Text>
                </TouchableOpacity>
              ) : (
                <View style={[styles.resultBox, { backgroundColor: theme.success + '15', borderColor: theme.success }]}>
                  <Text style={[styles.resultTitulo, { color: theme.text }]}>Sessão salva! 🎉</Text>
                  <Text style={[styles.resultSub, { color: theme.sub }]}>
                    {acertos} acertos de {respondidas} questões
                  </Text>
                  {/*
                    Antes: setMateria(materia) e setTipo(t => t). Os dois
                    gravavam o MESMO valor, e o React descarta um setState que
                    não muda nada — o efeito não rodava e o botão não fazia
                    absolutamente nada. Agora um contador dedicado muda de
                    verdade, então o efeito roda e a sessão é remontada.
                  */}
                  <TouchableOpacity accessibilityRole="button"
                    style={[styles.btnNovaSessao, { borderColor: theme.primary }]}
                    onPress={() => { setAba('Praticar'); setRecarga(r => r + 1); }}
                  >
                    <Text style={[styles.btnNovaSessaoTxt, { color: theme.primary }]}>
                      {modo === 'refazer' ? 'Revisar outras' : 'Nova Sessão'}
                    </Text>
                  </TouchableOpacity>

                  {modo === 'novas' && feitasDisponiveis > 0 && (
                    <TouchableOpacity accessibilityRole="button"
                      style={[styles.btnRefazer, { borderColor: theme.border }]}
                      onPress={() => alternarModo('refazer')}
                    >
                      <MaterialCommunityIcons name="history" size={17} color={theme.sub} />
                      <Text style={[styles.btnRefazerTxt, { color: theme.sub }]}>
                        Refazer já feitas ({feitasDisponiveis})
                      </Text>
                    </TouchableOpacity>
                  )}
                  {modo === 'refazer' && (
                    <TouchableOpacity accessibilityRole="button"
                      style={[styles.btnRefazer, { borderColor: theme.border }]}
                      onPress={() => alternarModo('novas')}
                    >
                      <MaterialCommunityIcons name="arrow-left" size={17} color={theme.sub} />
                      <Text style={[styles.btnRefazerTxt, { color: theme.sub }]}>
                        Voltar às inéditas
                      </Text>
                    </TouchableOpacity>
                  )}
                </View>
              )}
            </>
          )}
        </ScrollWrapper>
      )}

      {/* ============ ABA HISTÓRICO ============ */}
      {aba === 'Histórico' && (
        <ScrollWrapper>
          {carregandoHist ? (
            <ActivityIndicator size="large" color={theme.primary} style={{ marginTop: 40 }} />
          ) : (
            <>
              {/* Card de estatísticas gerais */}
              {stats && stats.totalRespondidas > 0 && (
                <View style={[styles.statsCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                  <Text style={[styles.statsTitulo, { color: theme.sub }]}>Desempenho Geral</Text>
                  <Text style={[styles.statsPercent, { color: theme.primary }]}>{stats.percentualGeral}%</Text>
                  <Text style={[styles.statsSub, { color: theme.sub }]}>
                    {stats.totalAcertos} acertos em {stats.totalRespondidas} questões • {stats.totalSessoes} sessões
                  </Text>

                  {/* Barras por matéria */}
                  {(Object.entries(stats.porMateria) as [string, { acertos: number; total: number; percentual: number }][])
                    .sort((a, b) => b[1].total - a[1].total)
                    .map(([mat, m]) => {
                      const cor = m.percentual >= 70 ? theme.success : m.percentual >= 50 ? theme.warning : theme.danger;
                      return (
                        <View key={mat} style={{ marginTop: 12 }}>
                          <View style={styles.matBarHeader}>
                            <Text style={[styles.matBarNome, { color: theme.text }]} numberOfLines={1}>{mat}</Text>
                            <Text style={[styles.matBarPct, { color: cor }]}>{m.percentual}%</Text>
                          </View>
                          <View style={[styles.barBg, { backgroundColor: theme.cardSec }]}>
                            <View style={[styles.barFill, { backgroundColor: cor, width: `${m.percentual}%` }]} />
                          </View>
                          <Text style={[styles.matBarDet, { color: theme.sub }]}>
                            {m.acertos} de {m.total} questões
                          </Text>
                        </View>
                      );
                    })}
                </View>
              )}

              {/* Lista de sessões */}
              {sessoes.length === 0 ? (
                <View style={[styles.emptyBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
                  <MaterialCommunityIcons name="history" size={48} color={theme.sub} />
                  <Text style={[styles.emptyTitle, { color: theme.text }]}>Nenhuma sessão ainda</Text>
                  <Text style={[styles.emptySub, { color: theme.sub }]}>
                    Pratique questões na aba "Praticar" e seu histórico aparece aqui.
                  </Text>
                  <TouchableOpacity accessibilityRole="button"
                    style={[styles.btnIrPraticar, { backgroundColor: theme.primary }]}
                    onPress={() => setAba('Praticar')}
                  >
                    <Text style={styles.btnIrPraticarTxt}>Ir Praticar</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                sessoes.map(s => {
                  const pct = s.total > 0 ? Math.round((s.acertos / s.total) * 100) : 0;
                  const cor = pct >= 70 ? theme.success : pct >= 50 ? theme.warning : theme.danger;
                  return (
                    <View key={s.id} style={[styles.sessaoCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                      <View style={styles.sessaoHeader}>
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.sessaoTitulo, { color: theme.text }]}>{s.materia}</Text>
                          <Text style={[styles.sessaoData, { color: theme.sub }]}>
                            {s.tipo} • {formatarDataQuestoes(s.data)}
                          </Text>
                        </View>
                        <View style={[styles.sessaoScore, { backgroundColor: cor + '20' }]}>
                          <Text style={[styles.sessaoScoreTxt, { color: cor }]}>{s.acertos}/{s.total}</Text>
                        </View>
                      </View>
                      <View style={styles.sessaoStats}>
                        <View style={styles.sessaoStat}>
                          <Ionicons name="checkmark-circle-outline" size={16} color={theme.success} />
                          <Text style={[styles.sessaoStatTxt, { color: theme.sub }]}>{s.acertos} acertos</Text>
                        </View>
                        <View style={styles.sessaoStat}>
                          <Ionicons name="close-circle-outline" size={16} color={theme.danger} />
                          <Text style={[styles.sessaoStatTxt, { color: theme.sub }]}>{s.erros} erros</Text>
                        </View>
                        <View style={styles.sessaoStat}>
                          <Ionicons name="stats-chart-outline" size={16} color={cor} />
                          <Text style={[styles.sessaoStatTxt, { color: cor }]}>{pct}%</Text>
                        </View>
                      </View>
                    </View>
                  );
                })
              )}
            </>
          )}
        </ScrollWrapper>
      )}

      {/* Guarda de sessão: pergunta antes de descartar o que foi respondido */}
      <NivelisModal {...modal} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, ...(Platform.OS === 'web' ? ({ height } as any) : {}) },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingTop: 50, paddingBottom: 15, paddingHorizontal: 20, borderBottomWidth: 1,
  },
  iconBtn: { padding: 5 },
  headerTitle: { fontSize: 18, fontWeight: 'bold' },

  abaContainer: { flexDirection: 'row', margin: 16, borderRadius: 12, padding: 4 },
  abaBtn: { flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8 },
  abaText: { fontWeight: 'bold', fontSize: 14 },

  scroll: { paddingHorizontal: 16, paddingBottom: 40 },

  tipoRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  tipoBtn: { flex: 1, paddingVertical: 10, borderRadius: 10, borderWidth: 1, alignItems: 'center' },
  tipoText: { fontWeight: 'bold', fontSize: 14 },

  chipsRow: { marginBottom: 14, maxHeight: 40 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, borderWidth: 1, marginRight: 8, maxWidth: 200 },
  chipText: { fontSize: 12, fontWeight: 'bold' },

  statusRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  badgeText: { fontSize: 11, fontWeight: 'bold' },
  contadorText: { fontSize: 13, fontWeight: '600' },

  qCard: { borderRadius: 16, borderWidth: 1, padding: 16, marginBottom: 16 },
  qHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  qNumero: { fontSize: 14, fontWeight: 'bold' },
  qMateria: { fontSize: 12, fontWeight: '600' },
  qContexto: { fontSize: 13, lineHeight: 19, marginBottom: 10, fontStyle: 'italic' },
  qEnunciado: { fontSize: 15, lineHeight: 23, marginBottom: 16 },

  alts: { gap: 10 },
  alt: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 12, borderWidth: 1, gap: 10 },
  altLetra: { width: 30, height: 30, borderRadius: 15, borderWidth: 1, justifyContent: 'center', alignItems: 'center' },
  altLetraTxt: { fontSize: 13, fontWeight: 'bold' },
  altTxt: { flex: 1, fontSize: 14, lineHeight: 20 },

  btnConfirmar: { marginTop: 16, paddingVertical: 12, borderRadius: 10, alignItems: 'center' },
  btnConfirmarTxt: { fontSize: 15, fontWeight: 'bold' },

  gabaritoBox: { marginTop: 16, padding: 14, borderRadius: 10 },
  gabaritoTitulo: { fontSize: 14, fontWeight: 'bold', marginBottom: 4 },
  gabaritoTexto: { fontSize: 13, lineHeight: 19 },

  btnFinalizar: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 14, borderRadius: 12, gap: 8, marginTop: 8 },
  btnFinalizarTxt: { fontSize: 15, fontWeight: 'bold' },

  resultBox: { padding: 20, borderRadius: 16, borderWidth: 1, alignItems: 'center', marginTop: 8 },
  resultTitulo: { fontSize: 18, fontWeight: 'bold', marginBottom: 4 },
  resultSub: { fontSize: 14, marginBottom: 16 },
  btnNovaSessao: { paddingVertical: 10, paddingHorizontal: 24, borderRadius: 10, borderWidth: 1 },
  btnNovaSessaoTxt: { fontSize: 14, fontWeight: 'bold' },

  // Refazer / modo de revisão
  btnRefazer: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    paddingVertical: 9, paddingHorizontal: 18, borderRadius: 10, borderWidth: 1,
    marginTop: 10,
  },
  btnRefazerTxt: { fontSize: 13, fontWeight: '600' },
  linhaRefazer: {
    flexDirection: 'row', alignItems: 'center', gap: 7,
    paddingVertical: 9, paddingHorizontal: 13, borderRadius: 10, borderWidth: 1,
    borderStyle: 'dashed', marginBottom: 12,
  },
  linhaRefazerTxt: { fontSize: 12.5, flex: 1 },
  faixaModo: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 10, paddingHorizontal: 13, borderRadius: 10, borderWidth: 1,
    marginBottom: 12,
  },
  faixaModoTxt: { fontSize: 13, fontWeight: '600', flex: 1 },
  faixaModoLink: { fontSize: 13, fontWeight: 'bold' },
  linhaOrigem: { fontSize: 11.5, textAlign: 'center', marginTop: 14, marginBottom: 2 },

  emptyBox: { borderRadius: 16, borderWidth: 1, padding: 32, alignItems: 'center', marginTop: 20 },
  emptyTitle: { fontSize: 17, fontWeight: 'bold', marginTop: 14, marginBottom: 6 },
  emptySub: { fontSize: 13, textAlign: 'center', lineHeight: 19 },
  btnIrPraticar: { marginTop: 16, paddingVertical: 12, paddingHorizontal: 28, borderRadius: 10 },
  btnIrPraticarTxt: { color: '#FFF', fontSize: 14, fontWeight: 'bold' },

  // Histórico
  statsCard: { borderRadius: 16, borderWidth: 1, padding: 20, marginBottom: 16, alignItems: 'center' },
  statsTitulo: { fontSize: 13, fontWeight: '600' },
  statsPercent: { fontSize: 42, fontWeight: 'bold', marginVertical: 4 },
  statsSub: { fontSize: 13, textAlign: 'center' },
  matBarHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6, width: '100%' },
  matBarNome: { fontSize: 13, fontWeight: '600', flex: 1, marginRight: 8 },
  matBarPct: { fontSize: 13, fontWeight: 'bold' },
  barBg: { height: 6, borderRadius: 3, overflow: 'hidden', width: '100%' },
  barFill: { height: 6, borderRadius: 3 },
  matBarDet: { fontSize: 11, marginTop: 4 },

  sessaoCard: { borderRadius: 16, borderWidth: 1, padding: 16, marginBottom: 12 },
  sessaoHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 },
  sessaoTitulo: { fontSize: 15, fontWeight: 'bold', marginBottom: 2 },
  sessaoData: { fontSize: 12 },
  sessaoScore: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  sessaoScoreTxt: { fontSize: 15, fontWeight: 'bold' },
  sessaoStats: { flexDirection: 'row', gap: 16 },
  sessaoStat: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  sessaoStatTxt: { fontSize: 12, fontWeight: '600' },
});