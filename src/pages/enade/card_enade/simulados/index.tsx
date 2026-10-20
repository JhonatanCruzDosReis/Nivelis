import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet, Text, View, Image, TouchableOpacity,
  FlatList, ScrollView, StatusBar, ImageBackground,
  Dimensions, ActivityIndicator
} from 'react-native';
import { Ionicons, MaterialCommunityIcons, FontAwesome5 } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useTheme } from '../../../TemasAcoes/Temas';
import {
  carregarHistorico, carregarEstatisticasPorMateria,
  HistoricoItem, MateriaStats,
} from '../../../../services/desempenhoService';
import { simuladosApi, questoesApi, MOCK_SIMULADOS, Simulado } from '../../../../services/apiService';

const { width } = Dimensions.get('window');
type FilterType = 'Disponíveis' | 'Histórico' | 'Desempenho';

const BANNER_FALLBACK = 'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?q=80&w=600';

function formatarData(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' });
  } catch { return iso; }
}

function formatarTempo(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0) return `${h}h ${m}min`;
  return `${m}min`;
}

export default function Simulados() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [nomeUsuario, setNomeUsuario]   = useState('Usuário');
  const [avatarUri,   setAvatarUri]     = useState<string | null>(null);
  const [activeTab,   setActiveTab]     = useState<'ENEM' | 'ENADE'>('ENEM');
  const [activeFilter, setActiveFilter] = useState<FilterType>('Disponíveis');

  // Desempenho / histórico
  const [historico,       setHistorico]       = useState<HistoricoItem[]>([]);
  const [statsPorMateria, setStatsPorMateria] = useState<Record<string, MateriaStats>>({});
  const [carregando,      setCarregando]      = useState(false);

  // Simulados — começa com mock, substituído pela API em background
  const [simuladosDisponiveis, setSimuladosDisponiveis] = useState<Simulado[]>(MOCK_SIMULADOS);
  const [questoesCount,        setQuestoesCount]        = useState<Record<string, number>>({});
  const [fonteSimulados,       setFonteSimulados]       = useState<'api' | 'demo'>('demo');
  const [apiCarregando,        setApiCarregando]        = useState(false);
  const [apiErro,              setApiErro]              = useState(false);
  const [retryCount,           setRetryCount]           = useState(0);

  const theme = {
    bg:           isDarkMode ? '#000000' : '#F5F5F7',
    card:         isDarkMode ? '#121214' : '#FFFFFF',
    cardSecondary:isDarkMode ? "#16161A"  : "#EAEAEA",
    text:         isDarkMode ? '#FFFFFF' : '#1A1A1A',
    textSecondary:isDarkMode ? '#A1A1AA' : '#666666',
    border:       isDarkMode ? '#27272A' : '#E5E5E5',
    primary:      '#7D53DD',
    primaryDark:  '#6D28D9',
    primaryLight: isDarkMode ? '#A78BFA' : '#6B59A0',   // 2.11 → 4.58 no claro
    success:      '#10B981',
    warning:      '#F59E0B',
    danger:       '#EF4444',
  };

  // ── Perfil + histórico: carrega ao focar na tela (1 vez) ─────────────────
  useFocusEffect(
    useCallback(() => {
      let alive = true;
      (async () => {
        // Perfil
        try {
          const raw = await AsyncStorage.getItem('@user_profile_data');
          if (raw && alive) {
            const d = JSON.parse(raw);
            if (d.nome)      setNomeUsuario(d.nome);
            if (d.avatarUri) setAvatarUri(d.avatarUri);
          }
        } catch {}

        // Histórico de desempenho
        setCarregando(true);
        try {
          const [hist, stats] = await Promise.all([
            carregarHistorico(),
            carregarEstatisticasPorMateria(),
          ]);
          if (alive) {
            setHistorico(hist);
            setStatsPorMateria(stats);
          }
        } catch {}
        if (alive) setCarregando(false);
      })();
      return () => { alive = false; };
    }, []),
  );

  // ── Simulados da API: recarrega ao trocar aba ─────────────────────────────
  useEffect(() => {
    let alive = true;
    setApiErro(false);
    setApiCarregando(true);

    // Mostra mock do tipo correto imediatamente enquanto carrega
    setSimuladosDisponiveis(MOCK_SIMULADOS.filter(s => s.tipo === activeTab));
    setFonteSimulados('demo');

    (async () => {
      try {
        // Tenta buscar simulados reais
        const sims = await simuladosApi.listar(activeTab);
        if (alive) {
          if (sims?.length > 0) {
            setSimuladosDisponiveis(sims);
            setFonteSimulados('api');
          } else {
            // API respondeu mas sem dados — mantém mock
            setSimuladosDisponiveis(MOCK_SIMULADOS.filter(s => s.tipo === activeTab));
            setFonteSimulados('demo');
          }
        }
      } catch {
        if (alive) {
          setSimuladosDisponiveis(MOCK_SIMULADOS.filter(s => s.tipo === activeTab));
          setFonteSimulados('demo');
          setApiErro(true);
        }
      }

      // Conta questões disponíveis (best-effort)
      try {
        const qs = await questoesApi.listar({ tipo: activeTab, limit: 20 });
        if (alive && qs?.length) {
          setQuestoesCount(prev => ({ ...prev, [activeTab]: qs.length }));
        }
      } catch {}

      if (alive) setApiCarregando(false);
    })();

    return () => { alive = false; };
  }, [activeTab, retryCount]);

  // Totais de desempenho
  const totalAcertos   = Object.values(statsPorMateria).reduce((s, v) => s + v.acertos, 0);
  const totalQuestoes  = Object.values(statsPorMateria).reduce((s, v) => s + v.total, 0);
  const aproveitamentoGeral = totalQuestoes > 0 ? Math.round((totalAcertos / totalQuestoes) * 100) : 0;

  const historicoFiltrado = historico.filter(h => h.tipo === activeTab);

  // ── CircleProgress ────────────────────────────────────────────────────────
  const CircleProgress = ({ percent, size = 70, label, color }: { percent: number; size?: number; label?: string; color?: string }) => {
    const pct        = Math.min(100, Math.max(0, percent));
    const scoreColor = pct >= 70 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444';
    const usedColor  = color ?? scoreColor;
    return (
      <View style={styles.circleContainer}>
        <View style={[styles.circleBase, { width: size, height: size, borderRadius: size / 2, borderColor: theme.cardSecondary }]}>
          <View style={[
            styles.circleFill, {
              width: size, height: size, borderRadius: size / 2,
              borderColor:       usedColor,
              borderTopColor:    usedColor,
              borderRightColor:  pct > 50  ? usedColor : 'transparent',
              borderBottomColor: pct > 75  ? usedColor : 'transparent',
              borderLeftColor:   'transparent',
              transform: [{ rotate: '45deg' }],
            },
          ]} />
          <View style={styles.circleTextContainer}>
            <Text style={[styles.circlePercent, { fontSize: size * 0.28, color: theme.text }]}>{pct}%</Text>
          </View>
        </View>
        {label && (
          <Text style={[styles.circleLabel, { color: theme.textSecondary }]} numberOfLines={1}>{label}</Text>
        )}
      </View>
    );
  };

  // ── RENDER ─────────────────────────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
          onPress={() => navigation.goBack()}
          style={[styles.iconButton, { backgroundColor: theme.cardSecondary }]}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <TouchableOpacity accessibilityRole="button" style={styles.rowCenter} onPress={() => navigation.navigate('MeusDados')} activeOpacity={0.7}>
          <View style={styles.userInfo}>
            <Text style={[styles.greetingText, { color: isDarkMode ? '#8C8C8C' : '#707070' }]}>BONS ESTUDOS,</Text>
            <Text style={[styles.userName, { color: theme.text }]}>{nomeUsuario}</Text>
          </View>
          {avatarUri ? (
            <Image source={{ uri: avatarUri }} style={styles.profilePic} />
          ) : (
            <View style={[styles.profilePic, styles.profilePlaceholder, { backgroundColor: theme.cardSecondary }]}>
              <FontAwesome5 name="user-alt" size={16} color={theme.primary} />
            </View>
          )}
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollPadding}>

        {/* ABAS ENEM / ENADE */}
        <View style={[styles.tabContainer, { backgroundColor: theme.card }]}>
          {(['ENEM', 'ENADE'] as const).map(tab => (
            <TouchableOpacity accessibilityRole="button"
              key={tab}
              style={[styles.tabBtn, activeTab === tab && { backgroundColor: theme.primary }]}
              onPress={() => setActiveTab(tab)}
            >
              <Text style={[styles.tabText, { color: activeTab === tab ? '#FFF' : theme.textSecondary }]}>{tab}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* FILTER CHIPS */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.chipsScroll} contentContainerStyle={{ paddingRight: 20 }}>
          {/* "Montar" não é filtro: leva para a tela que escolhe conteúdo e
              tamanho. Fica aqui porque é onde o usuário procura simulado. */}
          <TouchableOpacity accessibilityRole="button"
            style={[styles.chip, { backgroundColor: theme.primary, borderColor: theme.primary }]}
            onPress={() => navigation.navigate('MontarSimulado')}
          >
            <Text style={[styles.chipText, { color: '#FFF', fontWeight: '700' }]}>+ Montar</Text>
          </TouchableOpacity>
          {(['Disponíveis', 'Histórico', 'Desempenho'] as FilterType[]).map(filtro => {
            const isAtivo = activeFilter === filtro;
            return (
              <TouchableOpacity accessibilityRole="button"
                key={filtro}
                style={[styles.chip, { backgroundColor: isAtivo ? theme.primary + '20' : theme.card, borderColor: isAtivo ? theme.primary : theme.border }]}
                onPress={() => setActiveFilter(filtro)}
              >
                <Text style={[styles.chipText, { color: isAtivo ? theme.primaryLight : theme.textSecondary }]}>{filtro}</Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* ── DISPONÍVEIS ──────────────────────────────────────────────────── */}
        {activeFilter === 'Disponíveis' && (
          <View style={styles.sectionContainer}>
            {/* Título + badges de status */}
            <View style={styles.sectionTitleRow}>
              <MaterialCommunityIcons name="calendar-check" size={20} color={theme.primary} />
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Simulados {activeTab}</Text>

              {apiCarregando ? (
                <View style={[styles.fonteBadge, { backgroundColor: theme.cardSecondary }]}>
                  <ActivityIndicator size="small" color={theme.textSecondary} style={{ marginRight: 4 }} />
                  <Text style={[styles.fonteBadgeText, { color: theme.textSecondary }]}>Sincronizando...</Text>
                </View>
              ) : (
                <View style={[
                  styles.fonteBadge,
                  { backgroundColor: fonteSimulados === 'api' ? '#10B98120' : '#F59E0B20' },
                ]}>
                  <Text style={[
                    styles.fonteBadgeText,
                    { color: fonteSimulados === 'api' ? '#10B981' : '#F59E0B' },
                  ]}>
                    {fonteSimulados === 'api' ? '● Simulados oficiais'
                                              : '● Exemplos — servidor fora do ar'}
                  </Text>
                </View>
              )}

              {/* Botão de retry quando a API falhou */}
              {apiErro && !apiCarregando && (
                <TouchableOpacity accessibilityRole="button"
                  style={[styles.retryBtn, { borderColor: theme.danger }]}
                  onPress={() => setRetryCount(c => c + 1)}
                >
                  <Text style={{ color: theme.danger, fontSize: 11, fontWeight: 'bold' }}>↺ Tentar novamente</Text>
                </TouchableOpacity>
              )}
            </View>

            {/* Aviso de API offline */}
            {apiErro && !apiCarregando && (
              <View style={[styles.apiWarnBox, { backgroundColor: theme.warning + '15', borderColor: theme.warning + '40' }]}>
                <Ionicons name="cloud-offline-outline" size={16} color={theme.warning} />
                <Text style={[styles.apiWarnText, { color: theme.warning }]}>
                  {/* "cold-start" é jargão de quem hospeda, não de quem
                      estuda. E a frase não dizia o que fazer. */}
                  O servidor está fora do ar ou acordando — ele hiberna quando
                  ninguém usa. Estes são exemplos. Toque em Tentar novamente
                  em alguns segundos.
                </Text>
              </View>
            )}

            {/* Cards de simulados */}
            {simuladosDisponiveis.map((sim, i) => (
              <View key={String(sim.id) ?? String(i)} style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
                <ImageBackground
                  source={{ uri: sim.imagem ?? BANNER_FALLBACK }}
                  style={styles.bannerImg}
                  imageStyle={{ borderRadius: 12 }}
                >
                  <View style={styles.badge}>
                    <Text style={styles.badgeText}>{sim.tipo?.toUpperCase() ?? activeTab}</Text>
                  </View>
                </ImageBackground>
                <View style={styles.simuladoInfoRow}>
                  <View style={styles.simuladoTextCol}>
                    <Text style={[styles.simuladoTitle, { color: theme.text }]}>
                      {sim.titulo ?? `Simulado ${activeTab} #${i + 1}`}
                    </Text>
                    {sim.descricao ? (
                      <Text style={[styles.simuladoDesc, { color: theme.textSecondary }]} numberOfLines={2}>
                        {sim.descricao}
                      </Text>
                    ) : null}
                    <Text style={[styles.simuladoSub, { color: theme.textSecondary }]}>
                      {sim.total_questoes ?? sim.questoes?.length ?? '90'} questões  •  {sim.duracao_minutos ?? 270} min
                    </Text>
                  </View>
                  <TouchableOpacity accessibilityRole="button"
                    style={[styles.btnAction, { backgroundColor: theme.primary }]}
                    onPress={() => navigation.navigate('SimuladoAndamento', {
                      simuladoId: sim.id ?? null,
                      titulo:     sim.titulo ?? `Simulado ${activeTab}`,
                      tipo:       activeTab,
                    })}
                  >
                    <Text style={styles.btnActionText}>Iniciar</Text>
                    <Ionicons name="play" size={14} color="#FFF" style={{ marginLeft: 4 }} />
                  </TouchableOpacity>
                </View>
              </View>
            ))}

            {/* Início Rápido — usa questoesApi */}
            <TouchableOpacity accessibilityRole="button"
              style={[styles.btnQuickStart, { borderColor: theme.primary }]}
              onPress={() => navigation.navigate('SimuladoAndamento', {
                tipo:   activeTab,
                titulo: `Prática Rápida ${activeTab}`,
              })}
            >
              <MaterialCommunityIcons name="lightning-bolt" size={20} color={theme.primary} />
              <Text style={[styles.btnQuickStartText, { color: theme.primary }]}>
                Início Rápido — Questões {activeTab}
                {questoesCount[activeTab] ? ` (${questoesCount[activeTab]} disponíveis)` : ''}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── HISTÓRICO ────────────────────────────────────────────────────── */}
        {activeFilter === 'Histórico' && (
          <View style={styles.sectionContainer}>
            <View style={styles.sectionTitleRow}>
              <MaterialCommunityIcons name="history" size={20} color={theme.primary} />
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Histórico {activeTab}</Text>
            </View>

            {carregando ? (
              <ActivityIndicator color={theme.primary} style={{ marginTop: 20 }} />
            ) : historicoFiltrado.length === 0 ? (
              <View style={[styles.emptyBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
                <MaterialCommunityIcons name="clipboard-text-outline" size={48} color={theme.textSecondary} />
                <Text style={[styles.emptyTitle, { color: theme.text }]}>Nenhum simulado ainda</Text>
                <Text style={[styles.emptySub, { color: theme.textSecondary }]}>
                  Complete um simulado para ver seu histórico aqui.
                </Text>
                <TouchableOpacity accessibilityRole="button"
                  style={[styles.btnAction, { backgroundColor: theme.primary, marginTop: 16 }]}
                  onPress={() => setActiveFilter('Disponíveis')}
                >
                  <Text style={styles.btnActionText}>Ver Simulados</Text>
                </TouchableOpacity>
              </View>
            ) : (
              historicoFiltrado.map(item => {
                const pct      = item.total > 0 ? Math.round((item.acertos / item.total) * 100) : 0;
                const scoreCor = pct >= 70 ? '#10B981' : pct >= 50 ? '#F59E0B' : '#EF4444';
                return (
                  <View key={item.id} style={[styles.historyCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                    <View style={styles.historyHeader}>
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.simuladoTitle, { color: theme.text }]} numberOfLines={1}>{item.titulo}</Text>
                        <Text style={[styles.historyDate, { color: theme.textSecondary }]}>{formatarData(item.data)}</Text>
                      </View>
                      <View style={[styles.scoreBadge, { backgroundColor: scoreCor + '20' }]}>
                        <Text style={[styles.scoreBadgeText, { color: scoreCor }]}>{item.acertos}/{item.total}</Text>
                      </View>
                    </View>

                    <View style={styles.historyStatsRow}>
                      <View style={styles.historyStat}>
                        <Ionicons name="time-outline" size={16} color={theme.textSecondary} />
                        <Text style={[styles.historyStatText, { color: theme.textSecondary }]}>{formatarTempo(item.tempoSegundos)}</Text>
                      </View>
                      <View style={styles.historyStat}>
                        <Ionicons name="checkmark-circle-outline" size={16} color={scoreCor} />
                        <Text style={[styles.historyStatText, { color: scoreCor }]}>{pct}% de Acerto</Text>
                      </View>
                    </View>

                    <TouchableOpacity accessibilityRole="button"
                      style={[styles.btnGabarito, { borderColor: theme.primary }]}
                      onPress={() => navigation.navigate('GabaritoScreen', {
                        questoes:      item.questoes,
                        respostas:     item.respostas,
                        acertos:       item.acertos,
                        total:         item.total,
                        tempoSegundos: item.tempoSegundos,
                        titulo:        item.titulo,
                        tipo:          item.tipo,
                      })}
                    >
                      <Ionicons name="document-text-outline" size={18} color={theme.primaryLight} />
                      <Text style={[styles.btnGabaritoText, { color: theme.primaryLight }]}>Ver Gabarito Completo</Text>
                    </TouchableOpacity>
                  </View>
                );
              })
            )}
          </View>
        )}

        {/* ── DESEMPENHO ───────────────────────────────────────────────────── */}
        {activeFilter === 'Desempenho' && (
          <View style={styles.sectionContainer}>
            <View style={styles.sectionTitleRow}>
              <MaterialCommunityIcons name="poll" size={20} color={theme.primary} />
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Estatísticas Gerais</Text>
            </View>

            {carregando ? (
              <ActivityIndicator color={theme.primary} style={{ marginTop: 20 }} />
            ) : totalQuestoes === 0 ? (
              <View style={[styles.emptyBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
                <MaterialCommunityIcons name="chart-bar" size={48} color={theme.textSecondary} />
                <Text style={[styles.emptyTitle, { color: theme.text }]}>Sem dados ainda</Text>
                <Text style={[styles.emptySub, { color: theme.textSecondary }]}>
                  Conclua um simulado para visualizar seu desempenho por matéria.
                </Text>
                <TouchableOpacity accessibilityRole="button"
                  style={[styles.btnAction, { backgroundColor: theme.primary, marginTop: 16 }]}
                  onPress={() => setActiveFilter('Disponíveis')}
                >
                  <Text style={styles.btnActionText}>Fazer Simulado</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <>
                <View style={[styles.desempenhoMainCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                  <Text style={[styles.desempenhoMainTitle, { color: theme.textSecondary }]}>Aproveitamento Total</Text>
                  <View style={{ marginVertical: 20 }}>
                    <CircleProgress percent={aproveitamentoGeral} size={110} />
                  </View>
                  <Text style={[styles.desempenhoSubtext, { color: theme.textSecondary }]}>
                    {totalAcertos} acertos em {totalQuestoes} questões
                  </Text>
                  <Text style={[styles.desempenhoSubtext, { color: theme.textSecondary, marginTop: 4 }]}>
                    {historico.length} simulado(s) realizados
                  </Text>
                </View>

                <View style={styles.gridContainer}>
                  {Object.entries(statsPorMateria)
                    .sort((a, b) => b[1].percentualAcerto - a[1].percentualAcerto)
                    .map(([mat, stats]) => (
                      <View key={mat} style={[styles.gridCard, { backgroundColor: theme.card, borderColor: theme.border }]}>
                        <CircleProgress
                          percent={stats.percentualAcerto}
                          size={60}
                          label={mat.length > 10 ? mat.substring(0, 10) + '…' : mat}
                        />
                      </View>
                    ))
                  }
                </View>

                <Text style={[styles.sectionTitle, { color: theme.text, marginTop: 10 }]}>Por Matéria</Text>
                {Object.entries(statsPorMateria)
                  .sort((a, b) => a[1].percentualAcerto - b[1].percentualAcerto)
                  .map(([mat, stats]) => {
                    const barCor = stats.percentualAcerto >= 70 ? '#10B981' : stats.percentualAcerto >= 50 ? '#F59E0B' : '#EF4444';
                    return (
                      <View key={mat} style={[styles.materiaBar, { backgroundColor: theme.card, borderColor: theme.border }]}>
                        <View style={styles.materiaBarHeader}>
                          <Text style={[styles.materiaBarNome, { color: theme.text }]}>{mat}</Text>
                          <Text style={[styles.materiaBarPct, { color: barCor }]}>{stats.percentualAcerto}%</Text>
                        </View>
                        <View style={[styles.barBg, { backgroundColor: theme.cardSecondary }]}>
                          <View style={[styles.barFill, { backgroundColor: barCor, width: `${stats.percentualAcerto}%` }]} />
                        </View>
                        <Text style={[styles.materiaBarDetail, { color: theme.textSecondary }]}>
                          {stats.acertos} acertos de {stats.total} questões
                          {stats.horasBanco > 0 ? `  •  ${stats.horasBanco}h estudo recomendado` : ''}
                        </Text>
                      </View>
                    );
                  })
                }

                {Object.values(statsPorMateria).some(s => s.horasBanco > 0) && (
                  <TouchableOpacity accessibilityRole="button"
                    style={[styles.btnBancoHoras, { borderColor: '#F59E0B' }]}
                    onPress={() => navigation.navigate('GabaritoScreen', {
                      questoes:      historico[0]?.questoes ?? [],
                      respostas:     historico[0]?.respostas ?? {},
                      acertos:       historico[0]?.acertos ?? 0,
                      total:         historico[0]?.total ?? 0,
                      tempoSegundos: historico[0]?.tempoSegundos ?? 0,
                      titulo:        historico[0]?.titulo ?? 'Último Simulado',
                      tipo:          historico[0]?.tipo ?? 'ENEM',
                    })}
                  >
                    <MaterialCommunityIcons name="clock-alert-outline" size={20} color="#F59E0B" />
                    <Text style={[styles.btnBancoHorasText, { color: '#F59E0B' }]}>Ver Banco de Horas e Gerar Cronograma</Text>
                  </TouchableOpacity>
                )}
              </>
            )}
          </View>
        )}

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1 },
  scrollPadding:{ paddingBottom: 40, paddingHorizontal: 20 },
  sectionContainer: { marginTop: 10 },

  header:     { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 50, marginBottom: 20, paddingHorizontal: 20 },
  rowCenter:  { flexDirection: 'row', alignItems: 'center' },
  iconButton: { width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center' },
  userInfo:   { marginRight: 12, alignItems: 'flex-end' },
  greetingText: { fontSize: 10, fontWeight: 'bold' },
  userName:   { fontSize: 16, fontWeight: 'bold' },
  profilePic: { width: 38, height: 38, borderRadius: 19, borderWidth: 2, borderColor: '#7D53DD' },
  profilePlaceholder: { justifyContent: 'center', alignItems: 'center' },

  tabContainer: { flexDirection: 'row', borderRadius: 12, padding: 4, marginBottom: 15 },
  tabBtn:       { flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8 },
  tabText:      { fontWeight: 'bold', fontSize: 14 },

  chipsScroll: { marginBottom: 25, maxHeight: 40 },
  chip:        { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, borderWidth: 1, marginRight: 10 },
  chipText:    { fontSize: 13, fontWeight: 'bold' },

  sectionTitleRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 15, gap: 6 },
  sectionTitle:    { fontSize: 18, fontWeight: 'bold', marginLeft: 2, flex: 1 },
  fonteBadge:      { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8 },
  fonteBadgeText:  { fontSize: 11, fontWeight: 'bold' },
  retryBtn:        { borderWidth: 1, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 3 },

  apiWarnBox:  { flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderRadius: 10, padding: 10, marginBottom: 14 },
  apiWarnText: { fontSize: 12, flex: 1, lineHeight: 16 },

  // Cards
  card:         { borderRadius: 16, borderWidth: 1, padding: 12, marginBottom: 20 },
  bannerImg:    { width: '100%', height: 140, justifyContent: 'flex-end', padding: 12 },
  badge:        { backgroundColor: '#7D53DD', alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6 },
  badgeText:    { color: '#FFF', fontSize: 10, fontWeight: 'bold', letterSpacing: 0.5 },
  simuladoInfoRow:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 15, paddingHorizontal: 4 },
  simuladoTextCol:  { flex: 1, paddingRight: 12 },
  simuladoTitle:    { fontSize: 17, fontWeight: 'bold', marginBottom: 4 },
  simuladoDesc:     { fontSize: 12, lineHeight: 17, marginBottom: 4 },
  simuladoSub:      { fontSize: 13 },
  btnAction:    { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, borderRadius: 8 },
  btnActionText:{ color: '#FFF', fontWeight: 'bold', fontSize: 14 },

  btnQuickStart:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderRadius: 12, paddingVertical: 14, gap: 8, marginTop: 4 },
  btnQuickStartText: { fontWeight: 'bold', fontSize: 14 },

  // Histórico
  historyCard:     { borderRadius: 16, borderWidth: 1, padding: 20, marginBottom: 16 },
  historyHeader:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 15 },
  historyDate:     { fontSize: 12, marginTop: 4 },
  scoreBadge:      { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 8 },
  scoreBadgeText:  { fontWeight: 'bold', fontSize: 16 },
  historyStatsRow: { flexDirection: 'row', marginBottom: 20 },
  historyStat:     { flexDirection: 'row', alignItems: 'center', marginRight: 20 },
  historyStatText: { fontSize: 13, marginLeft: 6 },
  btnGabarito:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingVertical: 12, borderRadius: 8, borderWidth: 1 },
  btnGabaritoText: { fontWeight: 'bold', fontSize: 14, marginLeft: 8 },

  // Empty state
  emptyBox:   { borderRadius: 20, borderWidth: 1, padding: 40, alignItems: 'center', marginTop: 10 },
  emptyTitle: { fontSize: 18, fontWeight: 'bold', marginTop: 16, marginBottom: 8 },
  emptySub:   { fontSize: 14, textAlign: 'center', lineHeight: 20 },

  // Desempenho
  desempenhoMainCard:  { borderRadius: 16, borderWidth: 1, padding: 20, alignItems: 'center', marginBottom: 15 },
  desempenhoMainTitle: { fontSize: 14, fontWeight: 'bold' },
  desempenhoSubtext:   { fontSize: 12 },
  gridContainer: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between' },
  gridCard:      { width: '48%', borderRadius: 16, borderWidth: 1, paddingVertical: 20, alignItems: 'center', marginBottom: 15 },

  materiaBar:       { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 10 },
  materiaBarHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  materiaBarNome:   { fontSize: 14, fontWeight: 'bold', flex: 1 },
  materiaBarPct:    { fontSize: 14, fontWeight: 'bold' },
  materiaBarDetail: { fontSize: 11, marginTop: 6 },
  barBg:  { height: 6, borderRadius: 3, overflow: 'hidden' },
  barFill:{ height: 6, borderRadius: 3 },

  btnBancoHoras:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderRadius: 12, paddingVertical: 14, gap: 8, marginTop: 14, marginBottom: 4 },
  btnBancoHorasText: { fontWeight: 'bold', fontSize: 14 },

  // Circle Progress
  circleContainer:     { alignItems: 'center', justifyContent: 'center' },
  circleBase:          { borderWidth: 6, justifyContent: 'center', alignItems: 'center', position: 'relative' },
  circleFill:          { position: 'absolute', borderWidth: 6, top: -6, left: -6 },
  circleTextContainer: { position: 'absolute', width: '100%', height: '100%', justifyContent: 'center', alignItems: 'center' },
  circlePercent:       { fontWeight: 'bold' },
  circleLabel:         { fontSize: 10, fontWeight: 'bold', marginTop: 12, letterSpacing: 0.5, textAlign: 'center' },
});
