import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, StatusBar, ActivityIndicator
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation, useRoute } from '@react-navigation/native';
import { auth } from '../../../../services/firebase';
import { simuladosApi, questoesApi, questoesFeitasApi, MOCK_QUESTOES, Questao } from '../../../../services/apiService';
import { salvarHistorico } from '../../../../services/desempenhoService';
import { useTheme } from '../../../TemasAcoes/Temas';
import NivelisModal, { useNivelisModal } from '../../../../components/NivelisModal';

export default function SimuladoAndamentoScreen() {
  const navigation = useNavigation<any>();
  const route      = useRoute<any>();
  const { isDarkMode } = useTheme();
  const { modal, showModal } = useNivelisModal();

  const simuladoId = route.params?.simuladoId ?? null;
  const tipoParam  = (route.params?.tipo as 'ENEM' | 'ENADE') ?? 'ENEM';

  const [questoes,       setQuestoes]       = useState<Questao[]>([]);
  const [carregando,     setCarregando]     = useState(true);
  const [fonteQuestoes,  setFonteQuestoes]  = useState<'api' | 'demo'>('demo');
  const [indiceAtual,    setIndiceAtual]    = useState(0);
  const [respostas,      setRespostas]      = useState<Record<string, string>>({});
  const [tempoRestante,  setTempoRestante]  = useState(16200); // 4h30min
  const [enviando,       setEnviando]       = useState(false);

  const theme = {
    bg:          isDarkMode ? "#000000" : "#F5F5F7",
    card:        isDarkMode ? "#121214" : "#FFFFFF",
    cardSec:     isDarkMode ? "#18181B" : "#F0F0F0",
    text:        isDarkMode ? "#FFFFFF" : "#1A1A1A",
    sub:         isDarkMode ? "#A1A1AA" : "#666666",
    border:      isDarkMode ? "#27272A" : "#E5E5E5",
    primary:     "#8B5CF6",
    primaryLight:"#A78BFA",
    danger:      "#EF4444",
  };

  // Carrega questões: simulado específico OU questões aleatórias via questoesApi
  useEffect(() => {
    (async () => {
      setCarregando(true);
      try {
        if (simuladoId) {
          // Simulado específico — busca questoes reais (Firestore → REST → /montar)
          // Passa uid pra priorizar questoes que o usuario ainda nao fez
          const uid = auth.currentUser?.uid;
          const sim = await simuladosApi.buscarPorId(simuladoId, uid);
          if (sim?.questoes?.length) {
            setQuestoes(sim.questoes);
            setFonteQuestoes('api');
            setTempoRestante((sim.duracao_minutos ?? 270) * 60);
          } else {
            // Simulado sem questoes embarcadas — tenta carregar por materia
            // Extrai materia do titulo (ex: "ENEM 2022 — Humanas" → "humanas")
            const materiaSim = sim?.titulo?.split('—')?.[1]?.trim()?.toLowerCase();
            console.log('[SimuladoAndamento] Simulado vazio, tentando questoesApi com materia:', materiaSim);
            try {
              const qs = await questoesApi.listar({
                tipo: tipoParam,
                materia: materiaSim,
                limit: 10,
              });
              if (qs.length) {
                setQuestoes(qs);
                setFonteQuestoes('api');
              } else {
                setQuestoes(MOCK_QUESTOES);
                setFonteQuestoes('demo');
              }
            } catch {
              setQuestoes(MOCK_QUESTOES);
              setFonteQuestoes('demo');
            }
            setTempoRestante((sim?.duracao_minutos ?? 270) * 60);
          }
        } else {
          // Início Rápido: carrega questões reais via questoesApi
          try {
            const qs = await questoesApi.listar({ tipo: tipoParam, limit: 20 });
            if (qs.length) {
              setQuestoes(qs);
              setFonteQuestoes('api');
            } else {
              setQuestoes(MOCK_QUESTOES);
              setFonteQuestoes('demo');
            }
          } catch {
            setQuestoes(MOCK_QUESTOES);
            setFonteQuestoes('demo');
          }
          setTempoRestante(90 * 60); // 90 min para prática rápida
        }
      } catch {
        setQuestoes(MOCK_QUESTOES);
      } finally {
        setCarregando(false);
      }
    })();
  }, [simuladoId]);

  // Cronômetro
  useEffect(() => {
    if (carregando) return;
    const timer = setInterval(() => {
      setTempoRestante(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          finalizarSimulado(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [carregando]);

  const formatarTempo = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
  };

  const questaoAtual = questoes[indiceAtual];
  const progresso    = questoes.length > 0 ? ((indiceAtual + 1) / questoes.length) * 100 : 0;

  const handleSair = () => {
    showModal(
      'Pausar Simulado?',
      'Seu progresso atual será perdido. Deseja realmente sair?',
      'warning',
      [
        { text: 'Continuar', style: 'secondary', onPress: () => {} },
        { text: 'Sair',      style: 'danger',    onPress: () => navigation.goBack() },
      ],
    );
  };

  const finalizarSimulado = async (porTempo = false) => {
    if (!porTempo) {
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

  const enviarRespostas = async () => {
    setEnviando(true);
    try {
      const uid          = auth.currentUser?.uid ?? 'anonimo';
      const acertos      = questoes.filter(q => respostas[q.id] === q.gabarito).length;
      const tempoGasto   = 16200 - tempoRestante;
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

      // Save to local performance tracker
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

      // Marca as questoes respondidas como "feitas" no Firestore (anti-repeticao)
      // So marca as que o usuario realmente respondeu (nao as em branco)
      const idsRespondidas = questoes
        .filter(q => respostas[q.id] != null)
        .map(q => String(q.id));
      questoesFeitasApi.marcar(uid, idsRespondidas).catch(() => {});

      // Navigate to gabarito instead of showing a simple modal
      navigation.replace('GabaritoScreen', {
        questoes,
        respostas,
        acertos,
        total:         questoes.length,
        tempoSegundos: tempoGasto,
        titulo,
        tipo,
      });
    } catch (err) {
      console.error('Erro ao enviar resultado:', err);
      showModal('Erro', 'Não foi possível salvar o resultado. Tente novamente.', 'error');
    } finally {
      setEnviando(false);
    }
  };

  if (carregando) {
    return (
      <View style={[styles.container, { backgroundColor: theme.bg, justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={{ color: theme.sub, marginTop: 12 }}>Carregando simulado...</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />

      {/* HEADER */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={handleSair} style={styles.iconButton}>
          <Ionicons name="close" size={24} color={theme.text} />
        </TouchableOpacity>

        <View style={[styles.timerBox, { backgroundColor: theme.cardSec }]}>
          <Ionicons name="time-outline" size={16} color={tempoRestante < 1800 ? theme.danger : theme.text} />
          <Text style={[styles.timerText, { color: tempoRestante < 1800 ? theme.danger : theme.text }]}>
            {formatarTempo(tempoRestante)}
          </Text>
        </View>

        <TouchableOpacity style={styles.iconButton}>
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
                color: fonteQuestoes === 'api' ? '#10B981' : '#F59E0B',
              }}>
                {fonteQuestoes === 'api' ? '● API' : '● Demo'}
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
              <TouchableOpacity
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
        <TouchableOpacity
          style={[styles.navBtn, indiceAtual === 0 && { opacity: 0.3 }]}
          onPress={() => setIndiceAtual(i => i - 1)}
          disabled={indiceAtual === 0}
        >
          <Ionicons name="chevron-back" size={20} color={theme.text} />
          <Text style={[styles.navBtnText, { color: theme.text }]}>Anterior</Text>
        </TouchableOpacity>

        {indiceAtual === questoes.length - 1 ? (
          <TouchableOpacity
            style={[styles.btnFinalizar, { backgroundColor: theme.primary }, enviando && { opacity: 0.7 }]}
            onPress={() => finalizarSimulado(false)}
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
          <TouchableOpacity
            style={[styles.navBtn, { backgroundColor: theme.cardSec, borderRadius: 8, paddingHorizontal: 16 }]}
            onPress={() => setIndiceAtual(i => i + 1)}
          >
            <Text style={[styles.navBtnText, { color: theme.text }]}>Próxima</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.text} />
          </TouchableOpacity>
        )}
      </View>

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
