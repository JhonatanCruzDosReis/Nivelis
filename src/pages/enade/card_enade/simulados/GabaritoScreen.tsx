import React, { useState, useMemo } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, StatusBar, ActivityIndicator
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useTheme } from '../../../TemasAcoes/Temas';
import { Questao } from '../../../../services/apiService';
import {
  calcularBancoDeHoras,
  gerarEventosCronograma,
  getMateriaCor,
} from '../../../../services/desempenhoService';
import NivelisModal, { useNivelisModal } from '../../../../components/NivelisModal';

interface RouteParams {
  questoes:       Questao[];
  respostas:      Record<string, string>;
  acertos:        number;
  total:          number;
  tempoSegundos:  number;
  titulo:         string;
  tipo:           'ENEM' | 'ENADE';
}

function formatarTempo(s: number): string {
  const h  = Math.floor(s / 3600);
  const m  = Math.floor((s % 3600) / 60);
  const sc = s % 60;
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min ${sc}s`;
}

export default function GabaritoScreen() {
  const navigation = useNavigation<any>();
  const route      = useRoute<any>();
  const { isDarkMode } = useTheme();
  const { modal, showModal } = useNivelisModal();

  const {
    questoes       = [],
    respostas      = {},
    acertos        = 0,
    total          = 0,
    tempoSegundos  = 0,
    titulo         = 'Simulado',
    tipo           = 'ENEM',
  } = (route.params as RouteParams) ?? {};

  const [expandido, setExpandido]         = useState<Record<string, boolean>>({});
  const [gerandoCronograma, setGerandoCronograma] = useState(false);

  const theme = {
    bg:      isDarkMode ? '#000000' : '#F5F5F7',
    card:    isDarkMode ? '#121214' : '#FFFFFF',
    cardSec: isDarkMode ? '#18181B' : '#F0F0F0',
    text:    isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:     isDarkMode ? '#A1A1AA' : '#666666',
    border:  isDarkMode ? '#27272A' : '#E5E5E5',
    primary: '#7D53DD',
  };

  const porcentagem = total > 0 ? Math.round((acertos / total) * 100) : 0;

  // Compute per-subject breakdown from questoes + respostas
  const porMateria = useMemo(() => {
    const map: Record<string, { acertos: number; total: number }> = {};
    questoes.forEach(q => {
      const mat = q.materia ?? 'GERAL';
      if (!map[mat]) map[mat] = { acertos: 0, total: 0 };
      map[mat].total++;
      if (respostas[q.id] === q.gabarito) map[mat].acertos++;
    });
    return map;
  }, [questoes, respostas]);

  const bancoDeHoras = useMemo(() => calcularBancoDeHoras(porMateria), [porMateria]);

  const totalHorasBanco = Object.values(bancoDeHoras).reduce((s, h) => s + h, 0);

  // Summary row color
  const scoreCor = porcentagem >= 70 ? '#10B981' : porcentagem >= 50 ? '#F59E0B' : '#EF4444';

  const handleGerarCronograma = async () => {
    setGerandoCronograma(true);
    try {
      const n = await gerarEventosCronograma(bancoDeHoras);
      showModal(
        'Cronograma Atualizado! 📅',
        `${n} sessão(ões) de estudo foram adicionadas ao seu cronograma com base no seu desempenho.`,
        'success',
        [
          { text: 'Ver Cronograma', style: 'primary',    onPress: () => { navigation.navigate('Cronograma'); } },
          { text: 'Fechar',         style: 'secondary',  onPress: () => {} },
        ],
      );
    } catch (e) {
      showModal('Erro', 'Não foi possível gerar o cronograma. Tente novamente.', 'error');
    } finally {
      setGerandoCronograma(false);
    }
  };

  const toggleQuestao = (id: string) =>
    setExpandido(prev => ({ ...prev, [id]: !prev[id] }));

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* HEADER */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => navigation.navigate('SimuladosDashboard')} style={styles.headerBtn} hitSlop={{ top: 14, bottom: 14, left: 14, right: 14 }}
                            accessibilityRole="button"
                            accessibilityLabel="Voltar para os simulados"
                            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}>
          <Ionicons name="home-outline" size={22} color={theme.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]} numberOfLines={1}>{titulo}</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

        {/* ── SCORE CARD ── */}
        <View style={[styles.scoreCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
          <View style={[styles.scoreCircle, { borderColor: scoreCor }]}>
            <Text style={[styles.scoreNum, { color: scoreCor }]}>{porcentagem}%</Text>
            <Text style={[styles.scoreLabel, { color: theme.sub }]}>aproveitamento</Text>
          </View>

          <View style={styles.scoreDetails}>
            <Row icon="checkmark-circle" color="#10B981" label="Acertos" value={`${acertos}`} theme={theme} />
            <Row icon="close-circle"    color="#EF4444" label="Erros"   value={`${total - acertos}`} theme={theme} />
            <Row icon="time-outline"    color={theme.primary} label="Tempo" value={formatarTempo(tempoSegundos)} theme={theme} />
            <Row icon="list-outline"    color={theme.sub}    label="Total" value={`${total} questões`} theme={theme} />
          </View>
        </View>

        {/* ── POR MATÉRIA ── */}
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Desempenho por Matéria</Text>
        {Object.entries(porMateria).map(([mat, v]) => {
          const pct = v.total > 0 ? Math.round((v.acertos / v.total) * 100) : 0;
          const cor = getMateriaCor(mat);
          return (
            <View key={mat} style={[styles.materiaCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <View style={styles.materiaRow}>
                <View style={[styles.materiaDot, { backgroundColor: cor }]} />
                <Text style={[styles.materiaNome, { color: theme.text }]}>{mat}</Text>
                <Text style={[styles.materiaScore, { color: cor }]}>{pct}%</Text>
              </View>
              <View style={[styles.barBg, { backgroundColor: theme.cardSec }]}>
                <View style={[styles.barFill, { backgroundColor: cor, width: `${pct}%` }]} />
              </View>
              <Text style={[styles.materiaDetail, { color: theme.sub }]}>
                {v.acertos} acertos de {v.total} questões
              </Text>
            </View>
          );
        })}

        {/* ── BANCO DE HORAS ── */}
        {totalHorasBanco > 0 && (
          <>
            <View style={styles.bancoHeader}>
              <MaterialCommunityIcons name="clock-alert-outline" size={22} color="#F59E0B" />
              <Text style={[styles.sectionTitle, { color: theme.text, marginLeft: 8, marginBottom: 0 }]}>
                Banco de Horas
              </Text>
            </View>
            <Text style={[styles.bancoSub, { color: theme.sub }]}>
              Horas de estudo recomendadas por matéria com base nos seus erros
            </Text>

            {Object.entries(bancoDeHoras)
              .sort((a, b) => b[1] - a[1])
              .map(([mat, horas]) => {
                const cor = getMateriaCor(mat);
                return (
                  <View key={mat} style={[styles.bancoCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                    <View style={[styles.bancoIcon, { backgroundColor: cor + '20' }]}>
                      <MaterialCommunityIcons name="book-open-outline" size={20} color={cor} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.bancoMateria, { color: theme.text }]}>{mat}</Text>
                      <View style={[styles.barBg, { backgroundColor: theme.cardSec, marginTop: 6 }]}>
                        <View style={[styles.barFill, { backgroundColor: cor, width: `${(horas / 10) * 100}%` }]} />
                      </View>
                    </View>
                    <View style={[styles.bancoHorasBox, { backgroundColor: cor + '20' }]}>
                      <Text style={[styles.bancoHorasNum, { color: cor }]}>{horas}h</Text>
                    </View>
                  </View>
                );
              })}

            <TouchableOpacity
              style={[styles.btnCronograma, gerandoCronograma && { opacity: 0.7 }]}
              onPress={handleGerarCronograma}
              disabled={gerandoCronograma}
              activeOpacity={0.8}
            >
              {gerandoCronograma ? (
                <ActivityIndicator color="#FFF" size="small" />
              ) : (
                <>
                  <MaterialCommunityIcons name="calendar-plus" size={20} color="#FFF" />
                  <Text style={styles.btnCronogramaText}>Gerar Cronograma de Estudos</Text>
                </>
              )}
            </TouchableOpacity>
          </>
        )}

        {/* ── GABARITO QUESTÃO A QUESTÃO ── */}
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Gabarito Detalhado</Text>

        {questoes.map((q, idx) => {
          const resposta = respostas[q.id];
          const acertou  = resposta === q.gabarito;
          const open     = expandido[q.id] ?? false;

          return (
            <TouchableOpacity
              key={q.id}
              activeOpacity={0.85}
              onPress={() => toggleQuestao(String(q.id))}
              style={[
                styles.questaoCard,
                {
                  backgroundColor: theme.card,
                  borderColor: acertou ? '#10B981' : resposta ? '#EF4444' : theme.border,
                  borderLeftWidth: 4,
                  borderLeftColor: acertou ? '#10B981' : resposta ? '#EF4444' : '#F59E0B',
                },
              ]}
            >
              {/* Question header row */}
              <View style={styles.questaoRow}>
                <View style={[styles.questaoNumBox, { backgroundColor: acertou ? '#10B98120' : resposta ? '#EF444420' : '#F59E0B20' }]}>
                  <Text style={[styles.questaoNum, { color: acertou ? '#10B981' : resposta ? '#EF4444' : '#F59E0B' }]}>
                    {String(idx + 1).padStart(2, '0')}
                  </Text>
                </View>

                <View style={{ flex: 1, marginHorizontal: 12 }}>
                  {q.materia && (
                    <Text style={[styles.questaoMateria, { color: getMateriaCor(q.materia) }]}>{q.materia}</Text>
                  )}
                  <Text style={[styles.questaoEnunciado, { color: theme.text }]} numberOfLines={open ? undefined : 2}>
                    {q.enunciado}
                  </Text>
                </View>

                <Ionicons
                  name={acertou ? 'checkmark-circle' : resposta ? 'close-circle' : 'help-circle'}
                  size={26}
                  color={acertou ? '#10B981' : resposta ? '#EF4444' : '#F59E0B'}
                />
              </View>

              {/* Expanded: answer details */}
              {open && (
                <View style={[styles.questaoDetails, { borderTopColor: theme.border }]}>
                  {/* Alternatives */}
                  {q.alternativas.map(alt => {
                    const isGabarito   = alt.id === q.gabarito;
                    const isResposta   = alt.id === resposta;
                    const bgColor      = isGabarito
                      ? '#10B98115'
                      : isResposta && !acertou
                        ? '#EF444415'
                        : 'transparent';
                    const txtColor     = isGabarito ? '#10B981' : isResposta && !acertou ? '#EF4444' : theme.sub;
                    const letraColor   = isGabarito ? '#10B981' : isResposta && !acertou ? '#EF4444' : theme.sub;
                    const borderColor  = isGabarito ? '#10B981' : isResposta && !acertou ? '#EF4444' : theme.border;

                    return (
                      <View
                        key={alt.id}
                        style={[styles.altRow, { backgroundColor: bgColor, borderColor, borderWidth: 1, borderRadius: 8, marginBottom: 6 }]}
                      >
                        <View style={[styles.altLetra, { borderColor: letraColor }]}>
                          <Text style={[styles.altLetraText, { color: letraColor }]}>{alt.id}</Text>
                        </View>
                        <Text style={[styles.altTexto, { color: txtColor }]}>{alt.texto}</Text>
                        {isGabarito && <Ionicons name="checkmark" size={16} color="#10B981" style={{ marginLeft: 4 }} />}
                        {isResposta && !acertou && <Ionicons name="close" size={16} color="#EF4444" style={{ marginLeft: 4 }} />}
                      </View>
                    );
                  })}

                  {/* Summary */}
                  <View style={styles.respostaRow}>
                    <Text style={[styles.respostaLabel, { color: theme.sub }]}>Sua resposta: </Text>
                    <Text style={[styles.respostaVal, { color: resposta ? (acertou ? '#10B981' : '#EF4444') : '#F59E0B' }]}>
                      {resposta ?? 'Não respondida'}
                    </Text>
                    <Text style={[styles.respostaLabel, { color: theme.sub, marginLeft: 16 }]}>Gabarito: </Text>
                    <Text style={[styles.respostaVal, { color: '#10B981' }]}>{q.gabarito}</Text>
                  </View>
                </View>
              )}
            </TouchableOpacity>
          );
        })}

        <View style={{ height: 40 }} />
      </ScrollView>

      <NivelisModal {...modal} />
    </View>
  );
}

// ─── Small helper component ──────────────────────────────────────────────────
function Row({ icon, color, label, value, theme }: any) {
  return (
    <View style={styles.detailRow}>
      <Ionicons name={icon} size={16} color={color} />
      <Text style={[styles.detailLabel, { color: theme.sub }]}>{label}</Text>
      <Text style={[styles.detailValue, { color: theme.text }]}>{value}</Text>
    </View>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingTop: 50, paddingBottom: 15, paddingHorizontal: 20, borderBottomWidth: 1,
  },
  headerBtn:   { padding: 4 },
  headerTitle: { fontSize: 16, fontWeight: 'bold', flex: 1, textAlign: 'center', marginHorizontal: 8 },

  scroll: { padding: 20, paddingBottom: 40 },

  // Score card
  scoreCard: {
    flexDirection: 'row', alignItems: 'center',
    padding: 20, borderRadius: 20, borderWidth: 1, marginBottom: 28,
  },
  scoreCircle: {
    width: 110, height: 110, borderRadius: 55,
    borderWidth: 6, justifyContent: 'center', alignItems: 'center', marginRight: 20,
  },
  scoreNum:   { fontSize: 28, fontWeight: 'bold' },
  scoreLabel: { fontSize: 11, marginTop: 2 },
  scoreDetails: { flex: 1 },
  detailRow:  { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  detailLabel:{ fontSize: 12, marginLeft: 6, flex: 1 },
  detailValue:{ fontSize: 12, fontWeight: 'bold' },

  sectionTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 14 },

  // Matéria
  materiaCard: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 10 },
  materiaRow:  { flexDirection: 'row', alignItems: 'center', marginBottom: 8 },
  materiaDot:  { width: 10, height: 10, borderRadius: 5, marginRight: 8 },
  materiaNome: { flex: 1, fontSize: 14, fontWeight: 'bold' },
  materiaScore:{ fontSize: 14, fontWeight: 'bold' },
  materiaDetail:{ fontSize: 11, marginTop: 6 },
  barBg:  { height: 6, borderRadius: 3, overflow: 'hidden' },
  barFill:{ height: 6, borderRadius: 3 },

  // Banco de horas
  bancoHeader: { flexDirection: 'row', alignItems: 'center', marginBottom: 6, marginTop: 10 },
  bancoSub:    { fontSize: 12, marginBottom: 14 },
  bancoCard:   { flexDirection: 'row', alignItems: 'center', borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 10 },
  bancoIcon:   { width: 40, height: 40, borderRadius: 10, justifyContent: 'center', alignItems: 'center', marginRight: 12 },
  bancoMateria:{ fontSize: 14, fontWeight: 'bold' },
  bancoHorasBox:{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 10, marginLeft: 12 },
  bancoHorasNum:{ fontSize: 16, fontWeight: 'bold' },

  btnCronograma: {
    backgroundColor: '#7D53DD', flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    borderRadius: 14, paddingVertical: 16, paddingHorizontal: 20, gap: 10, marginVertical: 18,
  },
  btnCronogramaText: { color: '#FFF', fontSize: 15, fontWeight: 'bold' },

  // Questão card
  questaoCard: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 12 },
  questaoRow:  { flexDirection: 'row', alignItems: 'flex-start' },
  questaoNumBox:{ width: 38, height: 38, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  questaoNum:  { fontSize: 14, fontWeight: 'bold' },
  questaoMateria: { fontSize: 10, fontWeight: 'bold', letterSpacing: 0.5, marginBottom: 2 },
  questaoEnunciado: { fontSize: 13, lineHeight: 20 },
  questaoDetails: { marginTop: 14, paddingTop: 14, borderTopWidth: 1 },

  // Alternatives in expanded view
  altRow:    { flexDirection: 'row', alignItems: 'center', padding: 10 },
  altLetra:  { width: 28, height: 28, borderRadius: 14, borderWidth: 1, justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  altLetraText: { fontSize: 13, fontWeight: 'bold' },
  altTexto:  { flex: 1, fontSize: 13, lineHeight: 19 },

  respostaRow:  { flexDirection: 'row', alignItems: 'center', marginTop: 10, flexWrap: 'wrap' },
  respostaLabel:{ fontSize: 12 },
  respostaVal:  { fontSize: 13, fontWeight: 'bold' },
});
