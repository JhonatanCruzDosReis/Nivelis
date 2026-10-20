import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  StyleSheet, Text, View, Image, TouchableOpacity,
  ScrollView, TextInput, StatusBar, Modal, Linking,
  Dimensions, ActivityIndicator
} from 'react-native';
import { Ionicons, FontAwesome5, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useTheme } from '../../../TemasAcoes/Temas';
import {
  Livro,
  LIVROS_ENEM, LIVROS_ENADE,
  AREAS_ENADE, MATERIAS_ENEM,
} from '../../../../data/livrosData';

const { width } = Dimensions.get('window');
const PROGRESS_KEY = '@nivelis_livros_progresso';

// ─── Helpers ─────────────────────────────────────────────────────────────────
function progressoCor(pct: number): string {
  if (pct >= 75) return '#10B981';
  if (pct >= 40) return '#F59E0B';
  return '#7D53DD';
}

export default function LivrosScreen() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [nomeUsuario, setNomeUsuario] = useState('Usuário');
  const [avatarUri,   setAvatarUri]   = useState<string | null>(null);

  const [activeTab,   setActiveTab]   = useState<'ENEM' | 'ENADE'>('ENEM');
  const [filtroArea,  setFiltroArea]  = useState('Todas');
  const [busca,       setBusca]       = useState('');

  // Reading progress: livroId → percent (0-100)
  const [progresso, setProgresso] = useState<Record<string, number>>({});

  // Book detail modal
  const [livroSelecionado, setLivroSelecionado] = useState<Livro | null>(null);
  const [abrindoLink,      setAbrindoLink]      = useState(false);

  const theme = {
    bg:           isDarkMode ? '#050505' : '#F5F5F7',
    card:         isDarkMode ? '#121212' : '#FFFFFF',
    cardSec:      isDarkMode ? '#0D0D0D' : '#EBEBEB',
    text:         isDarkMode ? '#FFFFFF' : '#1A1A1A',
    textSec:      isDarkMode ? '#888888' : '#666666',
    border:       isDarkMode ? '#1A1A1A' : '#DDD',
    iconBg:       isDarkMode ? "#16161A"  : "#EAEAEA",
    primary:      '#7D53DD',
    primaryLight: isDarkMode ? '#A78BFA' : '#6B59A0',   // 2.11 → 4.58 no claro
    overlay:      isDarkMode ? 'rgba(0,0,0,0.85)' : 'rgba(0,0,0,0.5)',
  };

  // Load profile + progress
  useEffect(() => {
    (async () => {
      try {
        const raw = await AsyncStorage.getItem('@user_profile_data');
        if (raw) {
          const d = JSON.parse(raw);
          if (d.nome)      setNomeUsuario(d.nome);
          if (d.avatarUri) setAvatarUri(d.avatarUri);
        }
        const prog = await AsyncStorage.getItem(PROGRESS_KEY);
        if (prog) setProgresso(JSON.parse(prog));
      } catch {}
    })();
  }, []);

  // Save progress helper
  const saveProgress = useCallback(async (id: string, pct: number) => {
    const updated = { ...progresso, [id]: pct };
    setProgresso(updated);
    await AsyncStorage.setItem(PROGRESS_KEY, JSON.stringify(updated));
  }, [progresso]);

  // Filtered books
  const livrosFiltrados = useMemo(() => {
    const base = activeTab === 'ENEM' ? LIVROS_ENEM : LIVROS_ENADE;
    return base.filter(l => {
      // Area/Materia filter
      if (filtroArea !== 'Todas') {
        const campo = activeTab === 'ENADE' ? l.area : l.materia;
        if (campo !== filtroArea) return false;
      }
      // Search
      if (busca.trim()) {
        const q = busca.toLowerCase();
        return (
          l.titulo.toLowerCase().includes(q) ||
          l.autor.toLowerCase().includes(q) ||
          l.materia.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [activeTab, filtroArea, busca]);

  // Books in progress (pct > 0 and < 100)
  const emProgresso = useMemo(() => {
    const todos = [...LIVROS_ENEM, ...LIVROS_ENADE];
    return todos.filter(l => {
      const p = progresso[l.id] ?? 0;
      return p > 0 && p < 100;
    }).sort((a, b) => (progresso[b.id] ?? 0) - (progresso[a.id] ?? 0));
  }, [progresso]);

  const filtrosAtivos = activeTab === 'ENEM' ? MATERIAS_ENEM : AREAS_ENADE;

  // Open book link
  const handleAbrirLivro = async (livro: Livro) => {
    setAbrindoLink(true);
    try {
      await Linking.openURL(livro.link);
    } catch {}
    setAbrindoLink(false);
  };

  // Increment reading progress by 10% steps
  const handleAtualizarProgresso = async (livro: Livro, delta: number) => {
    const atual = progresso[livro.id] ?? 0;
    const novo  = Math.min(100, Math.max(0, atual + delta));
    await saveProgress(livro.id, novo);
  };

  // ── Book Card (horizontal list) ────────────────────────────────────────────
  const BookCard = ({ item }: { item: Livro }) => {
    const pct = progresso[item.id] ?? 0;
    const cor = progressoCor(pct);
    return (
      <TouchableOpacity accessibilityRole="button"
        style={styles.bookCard}
        activeOpacity={0.88}
        onPress={() => setLivroSelecionado(item)}
      >
        <View style={[styles.bookImageWrapper, { backgroundColor: theme.card }]}>
          <Image source={{ uri: item.capa }} style={styles.bookImage} />
          {pct > 0 && (
            <View style={[styles.progressPill, { backgroundColor: cor }]}>
              <Text style={styles.progressPillText}>{pct}%</Text>
            </View>
          )}
        </View>
        <Text style={[styles.bookTitle, { color: theme.text }]} numberOfLines={2}>{item.titulo}</Text>
        <Text style={[styles.bookAuthor, { color: theme.textSec }]} numberOfLines={1}>{item.autor}</Text>
        <View style={[styles.bookTag, { backgroundColor: theme.primary + '20' }]}>
          <Text style={[styles.bookTagText, { color: theme.primaryLight }]}>
            {activeTab === 'ENADE' ? item.area ?? item.materia : item.materia}
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  // ── Progress card ──────────────────────────────────────────────────────────
  const ProgressCard = ({ item }: { item: Livro }) => {
    const pct = progresso[item.id] ?? 0;
    const cor = progressoCor(pct);
    return (
      <TouchableOpacity
        style={[styles.progressCard, { backgroundColor: theme.cardSec, borderColor: theme.border }]}
        onPress={() => setLivroSelecionado(item)}
        activeOpacity={0.85}
      >
        <Image source={{ uri: item.capa }} style={styles.progressBookImage} />
        <View style={styles.progressTextColumn}>
          <Text style={[styles.progTitle, { color: theme.text }]} numberOfLines={2}>{item.titulo}</Text>
          <Text style={[styles.progAuthor, { color: theme.textSec }]}>{item.autor}</Text>
          <View style={[styles.progBarBg, { backgroundColor: isDarkMode ? '#222' : '#DDD' }]}>
            <View style={[styles.progBarFill, { backgroundColor: cor, width: `${pct}%` }]} />
          </View>
          <View style={styles.progInfoRow}>
            <Text style={[styles.progStatusText, { color: cor }]}>{pct}% lido</Text>
            <Text style={[styles.progPagesText, { color: theme.textSec }]}>{item.tipo}</Text>
          </View>
        </View>
        <TouchableOpacity
          style={[styles.resumeButton, { backgroundColor: theme.primary }]}
          onPress={() => handleAbrirLivro(item)}
          accessibilityRole="button"
          accessibilityLabel="Continuar a leitura"
        >
          <Ionicons name="play" size={18} color="#FFF" />
        </TouchableOpacity>
      </TouchableOpacity>
    );
  };

  // ── Book Detail Modal ──────────────────────────────────────────────────────
  const BookModal = () => {
    if (!livroSelecionado) return null;
    const l   = livroSelecionado;
    const pct = progresso[l.id] ?? 0;
    const cor = progressoCor(pct);

    return (
      <Modal
        visible={!!livroSelecionado}
        animationType="slide"
        transparent
        onRequestClose={() => setLivroSelecionado(null)}
      >
        <TouchableOpacity
          style={[styles.modalOverlay, { backgroundColor: theme.overlay }]}
          activeOpacity={1}
          onPress={() => setLivroSelecionado(null)}
        >
          <TouchableOpacity
            activeOpacity={1}
            style={[styles.modalSheet, { backgroundColor: theme.card }]}
            onPress={() => {}}
          >
            {/* Drag handle */}
            <View style={[styles.dragHandle, { backgroundColor: theme.border }]} />

            {/* Book header */}
            <View style={styles.modalHeader}>
              <Image source={{ uri: l.capa }} style={styles.modalBookImage} />
              <View style={styles.modalHeaderText}>
                <Text style={[styles.modalTitulo, { color: theme.text }]}>{l.titulo}</Text>
                <Text style={[styles.modalAutor, { color: theme.textSec }]}>{l.autor}</Text>
                <Text style={[styles.modalEditora, { color: theme.textSec }]}>{l.editora}</Text>
                <View style={styles.modalTagRow}>
                  <View style={[styles.bookTag, { backgroundColor: theme.primary + '20' }]}>
                    <Text style={[styles.bookTagText, { color: theme.primaryLight }]}>{l.materia}</Text>
                  </View>
                  {l.area && (
                    <View style={[styles.bookTag, { backgroundColor: '#F59E0B20', marginLeft: 6 }]}>
                      <Text style={[styles.bookTagText, { color: '#F59E0B' }]}>{l.area}</Text>
                    </View>
                  )}
                </View>
              </View>
            </View>

            {/* Description */}
            <Text style={[styles.modalDesc, { color: theme.textSec }]}>{l.descricao}</Text>

            {/* Stats row */}
            <View style={[styles.modalStats, { backgroundColor: theme.cardSec, borderRadius: 12 }]}>
              <View style={styles.statItem}>
                <Ionicons name="book-outline" size={18} color={theme.primary} />
                <Text style={[styles.statLabel, { color: theme.textSec }]}>{l.paginas} pág.</Text>
              </View>
              <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
              <View style={styles.statItem}>
                <MaterialCommunityIcons name="tag-outline" size={18} color={theme.primary} />
                <Text style={[styles.statLabel, { color: theme.textSec }]}>{l.tipo}</Text>
              </View>
              <View style={[styles.statDivider, { backgroundColor: theme.border }]} />
              <View style={styles.statItem}>
                <Ionicons name="bar-chart-outline" size={18} color={cor} />
                <Text style={[styles.statLabel, { color: cor }]}>{pct}% lido</Text>
              </View>
            </View>

            {/* Progress bar */}
            {pct > 0 && (
              <View style={styles.modalProgressRow}>
                <View style={[styles.progBarBg, { backgroundColor: isDarkMode ? '#222' : '#DDD', flex: 1 }]}>
                  <View style={[styles.progBarFill, { backgroundColor: cor, width: `${pct}%` }]} />
                </View>
              </View>
            )}

            {/* Progress controls */}
            <View style={styles.progressControls}>
              <Text style={[styles.progressControlLabel, { color: theme.textSec }]}>Atualizar progresso:</Text>
              <View style={styles.progressBtns}>
                <TouchableOpacity
                  style={[styles.progressBtn, { backgroundColor: theme.cardSec }]}
                  onPress={() => handleAtualizarProgresso(l, -10)}
                  disabled={pct <= 0}
                  accessibilityRole="button"
                  accessibilityLabel="Remover"
                >
                  <Ionicons name="remove" size={18} color={pct <= 0 ? theme.border : theme.text} />
                </TouchableOpacity>
                <Text style={[styles.progressPctText, { color: theme.text }]}>{pct}%</Text>
                <TouchableOpacity
                  style={[styles.progressBtn, { backgroundColor: theme.cardSec }]}
                  onPress={() => handleAtualizarProgresso(l, 10)}
                  disabled={pct >= 100}
                  accessibilityRole="button"
                  accessibilityLabel="Adicionar"
                >
                  <Ionicons name="add" size={18} color={pct >= 100 ? theme.border : theme.text} />
                </TouchableOpacity>
              </View>
            </View>

            {/* Action buttons */}
            <TouchableOpacity accessibilityRole="button"
              style={[styles.btnAbrirLivro, abrindoLink && { opacity: 0.7 }]}
              onPress={() => handleAbrirLivro(l)}
              disabled={abrindoLink}
            >
              {abrindoLink ? (
                <ActivityIndicator color="#FFF" size="small" />
              ) : (
                <>
                  <Ionicons name="open-outline" size={20} color="#FFF" />
                  <Text style={styles.btnAbrirLivroText}>Abrir / Comprar Livro</Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity accessibilityRole="button"
              style={[styles.btnFechar, { borderColor: theme.border }]}
              onPress={() => setLivroSelecionado(null)}
            >
              <Text style={[styles.btnFecharText, { color: theme.textSec }]}>Fechar</Text>
            </TouchableOpacity>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    );
  };

  // ── Main render ────────────────────────────────────────────────────────────
  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
          onPress={() => navigation.navigate('EnemEnade')}
          style={[styles.iconButton, { backgroundColor: theme.iconBg }]}
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
            <View style={[styles.profilePic, styles.profilePlaceholder, { backgroundColor: theme.iconBg }]}>
              <FontAwesome5 name="user-alt" size={18} color={theme.primary} />
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* ENEM / ENADE TABS */}
      <View style={[styles.tabContainer, { backgroundColor: theme.card, marginHorizontal: 20 }]}>
        {(['ENEM', 'ENADE'] as const).map(tab => (
          <TouchableOpacity accessibilityRole="button"
            key={tab}
            style={[styles.tabBtn, activeTab === tab && { backgroundColor: theme.primary }]}
            onPress={() => { setActiveTab(tab); setFiltroArea('Todas'); setBusca(''); }}
          >
            <Text style={[styles.tabText, { color: activeTab === tab ? '#FFF' : theme.textSec }]}>{tab}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollPadding}>

        {/* SEARCH */}
        <View style={[styles.searchBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
          <Ionicons name="search" size={20} color={theme.textSec} />
          <TextInput
            placeholder={`Buscar livros de ${activeTab}...`}
            placeholderTextColor={theme.textSec}
            style={[styles.searchInput, { color: theme.text }]}
            value={busca}
            onChangeText={setBusca}
          />
          {busca.length > 0 && (
            <TouchableOpacity onPress={() => setBusca('')}
              accessibilityRole="button"
              accessibilityLabel="Fechar"
            >
              <Ionicons name="close-circle" size={18} color={theme.textSec} />
            </TouchableOpacity>
          )}
        </View>

        {/* AREA FILTERS */}
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
          {filtrosAtivos.map(cat => (
            <TouchableOpacity accessibilityRole="button"
              key={cat}
              onPress={() => setFiltroArea(cat)}
              style={[
                styles.filterChip,
                { backgroundColor: theme.card, borderColor: theme.border },
                filtroArea === cat && { backgroundColor: theme.primary, borderColor: theme.primary },
              ]}
            >
              <Text style={[
                styles.filterChipText,
                { color: filtroArea === cat ? '#FFF' : theme.textSec },
              ]}>{cat}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* BOOKS LIST */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>
            {activeTab === 'ENEM' ? '📚 Livros ENEM' : '🎓 Livros ENADE'}
          </Text>
          <Text style={[styles.countText, { color: theme.textSec }]}>{livrosFiltrados.length} livros</Text>
        </View>

        {livrosFiltrados.length === 0 ? (
          <View style={[styles.emptyBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Ionicons name="search-outline" size={40} color={theme.textSec} />
            <Text style={[styles.emptyText, { color: theme.textSec }]}>Nenhum livro encontrado</Text>
          </View>
        ) : (
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ paddingLeft: 20, paddingRight: 6 }}>
            {livrosFiltrados.map(l => <BookCard key={l.id} item={l} />)}
          </ScrollView>
        )}

        {/* ALL BOOKS GRID */}
        {busca === '' && (
          <>
            <View style={[styles.sectionHeader, { marginTop: 28 }]}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Todos os Livros</Text>
            </View>
            <View style={styles.gridBooks}>
              {livrosFiltrados.map(l => {
                const pct = progresso[l.id] ?? 0;
                const cor = progressoCor(pct);
                return (
                  <TouchableOpacity accessibilityRole="button"
                    key={l.id}
                    style={[styles.gridBookCard, { backgroundColor: theme.card, borderColor: theme.border }]}
                    onPress={() => setLivroSelecionado(l)}
                    activeOpacity={0.85}
                  >
                    <Image source={{ uri: l.capa }} style={styles.gridBookImage} />
                    <View style={styles.gridBookInfo}>
                      <Text style={[styles.gridBookTitle, { color: theme.text }]} numberOfLines={2}>{l.titulo}</Text>
                      <Text style={[styles.gridBookAutor, { color: theme.textSec }]} numberOfLines={1}>{l.autor}</Text>
                      {pct > 0 && (
                        <View style={[styles.progBarBg, { backgroundColor: isDarkMode ? '#222' : '#DDD', marginTop: 6 }]}>
                          <View style={[styles.progBarFill, { backgroundColor: cor, width: `${pct}%` }]} />
                        </View>
                      )}
                    </View>
                    <Ionicons name="chevron-forward" size={18} color={theme.textSec} />
                  </TouchableOpacity>
                );
              })}
            </View>
          </>
        )}

        {/* CONTINUE READING */}
        {emProgresso.length > 0 && (
          <>
            <View style={[styles.sectionHeader, { marginTop: 28 }]}>
              <Text style={[styles.sectionTitle, { color: theme.text }]}>Continue Lendo</Text>
            </View>
            {emProgresso.map(l => <ProgressCard key={l.id} item={l} />)}
          </>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>

      <BookModal />
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1 },
  scrollPadding:{ paddingBottom: 50 },

  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    marginTop: 55, marginBottom: 16, paddingHorizontal: 20,
  },
  rowCenter:    { flexDirection: 'row', alignItems: 'center' },
  userInfo:     { marginRight: 10, alignItems: 'flex-end' },
  greetingText: { fontSize: 10, fontWeight: 'bold' },
  userName:     { fontSize: 16, fontWeight: 'bold' },
  profilePic:   { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: '#7D53DD' },
  profilePlaceholder: { justifyContent: 'center', alignItems: 'center' },
  iconButton:   { padding: 10, borderRadius: 50 },

  // Tabs
  tabContainer: { flexDirection: 'row', borderRadius: 12, padding: 4, marginBottom: 18 },
  tabBtn:       { flex: 1, paddingVertical: 12, alignItems: 'center', borderRadius: 8 },
  tabText:      { fontWeight: 'bold', fontSize: 14 },

  // Search
  searchBox: {
    flexDirection: 'row', alignItems: 'center',
    marginHorizontal: 20, paddingHorizontal: 15,
    height: 52, borderRadius: 14, borderWidth: 1, marginBottom: 18,
  },
  searchInput: { flex: 1, marginLeft: 10, fontSize: 15 },

  // Filters
  filterScroll: { paddingLeft: 20, marginBottom: 24 },
  filterChip:   { paddingHorizontal: 20, paddingVertical: 9, borderRadius: 22, marginRight: 10, borderWidth: 1 },
  filterChipText: { fontWeight: 'bold', fontSize: 13 },

  // Section header
  sectionHeader: {
    flexDirection: 'row', justifyContent: 'space-between',
    alignItems: 'center', paddingHorizontal: 22, marginBottom: 14,
  },
  sectionTitle: { fontSize: 20, fontWeight: 'bold' },
  countText:    { fontSize: 12 },

  // Horizontal book cards
  bookCard:         { width: 145, marginRight: 20 },
  bookImageWrapper: { width: 145, height: 200, borderRadius: 16, overflow: 'hidden', marginBottom: 10, elevation: 4, position: 'relative' },
  bookImage:        { width: '100%', height: '100%' },
  progressPill:     { position: 'absolute', top: 8, right: 8, borderRadius: 10, paddingHorizontal: 8, paddingVertical: 3 },
  progressPillText: { color: '#FFF', fontSize: 10, fontWeight: 'bold' },
  bookTitle:        { fontSize: 14, fontWeight: 'bold', marginBottom: 2 },
  bookAuthor:       { fontSize: 12, marginBottom: 6 },
  bookTag:          { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  bookTagText:      { fontSize: 10, fontWeight: 'bold' },

  // Grid books
  gridBooks:        { paddingHorizontal: 20 },
  gridBookCard:     { flexDirection: 'row', alignItems: 'center', borderRadius: 14, borderWidth: 1, padding: 12, marginBottom: 10 },
  gridBookImage:    { width: 56, height: 76, borderRadius: 8, marginRight: 12 },
  gridBookInfo:     { flex: 1 },
  gridBookTitle:    { fontSize: 14, fontWeight: 'bold', marginBottom: 2 },
  gridBookAutor:    { fontSize: 12 },

  // Progress cards
  progressCard:       { marginHorizontal: 20, borderRadius: 20, padding: 14, flexDirection: 'row', alignItems: 'center', borderWidth: 1, marginBottom: 12 },
  progressBookImage:  { width: 60, height: 84, borderRadius: 10 },
  progressTextColumn: { flex: 1, marginLeft: 14 },
  progTitle:          { fontSize: 15, fontWeight: 'bold' },
  progAuthor:         { fontSize: 12, marginBottom: 10 },
  progBarBg:          { height: 5, borderRadius: 3 },
  progBarFill:        { height: 5, borderRadius: 3, backgroundColor: '#7D53DD' },
  progInfoRow:        { flexDirection: 'row', justifyContent: 'space-between', marginTop: 5 },
  progStatusText:     { fontSize: 10, fontWeight: 'bold' },
  progPagesText:      { fontSize: 10 },
  resumeButton:       { width: 40, height: 40, borderRadius: 20, justifyContent: 'center', alignItems: 'center', marginLeft: 10 },

  // Empty
  emptyBox:  { marginHorizontal: 20, borderRadius: 16, borderWidth: 1, padding: 40, alignItems: 'center' },
  emptyText: { marginTop: 12, fontSize: 14 },

  // Modal
  modalOverlay: { flex: 1, justifyContent: 'flex-end' },
  modalSheet:   { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, maxHeight: '90%' },
  dragHandle:   { width: 40, height: 4, borderRadius: 2, alignSelf: 'center', marginBottom: 20 },
  modalHeader:  { flexDirection: 'row', marginBottom: 16 },
  modalBookImage: { width: 90, height: 126, borderRadius: 12, marginRight: 16 },
  modalHeaderText: { flex: 1, justifyContent: 'center' },
  modalTitulo:  { fontSize: 16, fontWeight: 'bold', marginBottom: 4, lineHeight: 22 },
  modalAutor:   { fontSize: 13, marginBottom: 2 },
  modalEditora: { fontSize: 12, marginBottom: 10 },
  modalTagRow:  { flexDirection: 'row', flexWrap: 'wrap' },
  modalDesc:    { fontSize: 13, lineHeight: 20, marginBottom: 16 },
  modalStats:   { flexDirection: 'row', padding: 14, marginBottom: 16 },
  statItem:     { flex: 1, alignItems: 'center', gap: 4 },
  statLabel:    { fontSize: 12, marginTop: 4 },
  statDivider:  { width: 1, marginVertical: 4 },
  modalProgressRow: { marginBottom: 16 },

  progressControls:     { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 },
  progressControlLabel: { fontSize: 13 },
  progressBtns:         { flexDirection: 'row', alignItems: 'center', gap: 12 },
  progressBtn:          { width: 36, height: 36, borderRadius: 18, justifyContent: 'center', alignItems: 'center' },
  progressPctText:      { fontSize: 16, fontWeight: 'bold', minWidth: 42, textAlign: 'center' },

  btnAbrirLivro:     { backgroundColor: '#7D53DD', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', borderRadius: 14, paddingVertical: 14, gap: 10, marginBottom: 12 },
  btnAbrirLivroText: { color: '#FFF', fontSize: 15, fontWeight: 'bold' },
  btnFechar:         { borderWidth: 1, borderRadius: 14, paddingVertical: 12, alignItems: 'center' },
  btnFecharText:     { fontSize: 14, fontWeight: 'bold' },
});
