import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, StatusBar, ActivityIndicator, Dimensions, Platform,
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { auth } from '../../../../services/firebase';
import { questoesApi, questoesFeitasApi, MOCK_QUESTOES, Questao } from '../../../../services/apiService';
import {
  salvarSessaoQuestoes, carregarSessoesQuestoes, carregarStatsQuestoes,
  SessaoQuestoes, QuestoesStats, formatarDataQuestoes,
} from '../../../../services/questoesService';
import { useTheme } from '../../../TemasAcoes/Temas';

const QUESTOES_POR_SESSAO = 10;
type Aba = 'Praticar' | 'Histórico';

const { height } = Dimensions.get('window');

// Matérias por tipo (chips de filtro)
const MATERIAS: Record<'ENEM' | 'ENADE', string[]> = {
  ENEM:  ['Todas', 'Matemática', 'Linguagens', 'Humanas', 'Natureza'],
  ENADE: ['Todas', 'Redes de Computadores', 'Análise e Desenvolvimento de Sistemas', 'Direito', 'Administração'],
};

export default function QuestoesScreen() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [aba, setAba]           = useState<Aba>('Praticar');
  const [tipo, setTipo]         = useState<'ENEM' | 'ENADE'>('ENEM');
  const [materia, setMateria]   = useState('Todas');

  // Praticar
  const [questoes, setQuestoes]               = useState<Questao[]>([]);
  const [carregando, setCarregando]           = useState(true);
  const [fonteQuestoes, setFonteQuestoes]     = useState<'api' | 'demo'>('demo');
  const [respostas, setRespostas]             = useState<Record<string, string>>({});
  const [confirmadas, setConfirmadas]         = useState<Record<string, boolean>>({});
  const [finalizada, setFinalizada]           = useState(false);

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
    primary:   "#EC4899",  // rosa (cor do card Questões)
    primaryLt: "#F472B6",
    success:   "#10B981",
    danger:    "#EF4444",
    warning:   "#F59E0B",
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
        const uid = auth.currentUser?.uid;
        // listarDoBanco: busca questões existentes SEM gerar (economiza tokens)
        const qs = await questoesApi.listarDoBanco({
          tipo,
          materia: materia === 'Todas' ? undefined : materia,
          limit: QUESTOES_POR_SESSAO,
          uid,
        });

        if (!ativo) return;

        if (qs.length > 0) {
          setQuestoes(qs);
          setFonteQuestoes('api');
        } else {
          setQuestoes(MOCK_QUESTOES.filter((q: Questao) => q.tipo === tipo));
          setFonteQuestoes('demo');
        }
      } catch {
        if (!ativo) return;
        setQuestoes(MOCK_QUESTOES.filter((q: Questao) => q.tipo === tipo));
        setFonteQuestoes('demo');
      } finally {
        if (ativo) setCarregando(false);
      }
    })();

    return () => { ativo = false; };
  }, [tipo, materia, aba]);

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
    // Salva sessão no histórico
    await salvarSessaoQuestoes(tipo, materia, questoes, respostas);
    // Marca questões como feitas (anti-repetição)
    const uid = auth.currentUser?.uid ?? 'anonimo';
    const ids = questoes.filter(q => respostas[q.id] != null).map(q => String(q.id));
    questoesFeitasApi.marcar(uid, ids).catch(() => {});
  };

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
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.iconBtn}>
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Questões</Text>
        <View style={{ width: 30 }} />
      </View>

      {/* ABAS Praticar | Histórico */}
      <View style={[styles.abaContainer, { backgroundColor: theme.card }]}>
        {(['Praticar', 'Histórico'] as Aba[]).map(a => (
          <TouchableOpacity
            key={a}
            style={[styles.abaBtn, aba === a && { backgroundColor: theme.primary }]}
            onPress={() => setAba(a)}
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
              <TouchableOpacity
                key={t}
                style={[
                  styles.tipoBtn,
                  { borderColor: tipo === t ? theme.primary : theme.border },
                  tipo === t && { backgroundColor: theme.primary + '15' },
                ]}
                onPress={() => setTipo(t)}
              >
                <Text style={[styles.tipoText, { color: tipo === t ? theme.primary : theme.sub }]}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Chips de matéria */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsRow} contentContainerStyle={{ paddingRight: 16 }}>
            {MATERIAS[tipo].map(m => (
              <TouchableOpacity
                key={m}
                style={[
                  styles.chip,
                  { backgroundColor: materia === m ? theme.primary + '20' : theme.card, borderColor: materia === m ? theme.primary : theme.border },
                ]}
                onPress={() => setMateria(m)}
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
              <Text style={[styles.badgeText, { color: fonteQuestoes === 'api' ? theme.success : theme.warning }]}>
                {fonteQuestoes === 'api' ? '● Banco' : '● Demo'}
              </Text>
            </View>
            {respondidas > 0 && (
              <Text style={[styles.contadorText, { color: theme.sub }]}>
                {acertos} acertos / {respondidas} respondidas
              </Text>
            )}
          </View>

          {/* Lista de questões */}
          {carregando ? (
            <ActivityIndicator size="large" color={theme.primary} style={{ marginTop: 40 }} />
          ) : questoes.length === 0 ? (
            <View style={[styles.emptyBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <MaterialCommunityIcons name="help-circle-outline" size={48} color={theme.sub} />
              <Text style={[styles.emptyTitle, { color: theme.text }]}>Sem questões aqui ainda</Text>
              <Text style={[styles.emptySub, { color: theme.sub }]}>
                Tente outra matéria ou gere questões indexando provas/livros.
              </Text>
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
                      <Text style={[styles.qMateria, { color: theme.sub }]}>{q.materia ?? 'Geral'}</Text>
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
                          <TouchableOpacity
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
                      <TouchableOpacity
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
              {!finalizada ? (
                <TouchableOpacity
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
                  <TouchableOpacity
                    style={[styles.btnNovaSessao, { borderColor: theme.primary }]}
                    onPress={() => { setMateria(materia); setAba('Praticar'); /* recarrega */ setTipo(t => t); }}
                  >
                    <Text style={[styles.btnNovaSessaoTxt, { color: theme.primary }]}>Nova Sessão</Text>
                  </TouchableOpacity>
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
                  <TouchableOpacity
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
