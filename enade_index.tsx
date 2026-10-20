import React, { useState, useEffect, useCallback } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  Image, 
  TouchableOpacity, 
  FlatList, 
  ScrollView, 
  ImageBackground,
  Dimensions,
  ActivityIndicator,
  Linking,
  SafeAreaView,
  StatusBar,
  Platform
} from 'react-native';
import { Ionicons, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// IMPORTAÇÃO DA CHAVE SEGURA E TEMA
import { GNEWS_API_KEY } from '@env';
import { useTheme } from '../TemasAcoes/Temas';

const { width, height } = Dimensions.get('window');

interface Noticia {
  titulo: string;
  imagem: string;
  link: string;
  tag: string;
}

export default function EnemEnadePage() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const theme = {
    bg: isDarkMode ? "#000000" : "#F5F5F7",
    card: isDarkMode ? "#15151C" : "#FFFFFF",
    arrow: isDarkMode ? "#16161A"  : "#EAEAEA",
    text: isDarkMode ? "#FFFFFF" : "#333333",
    textSecondary: isDarkMode ? "#666666" : "#999999",
    border: isDarkMode ? "#222222" : "#DDDDDD",
    icon: isDarkMode ? "#ffff" : "#202024",
    navBg: isDarkMode ? "#000000" : "#FFFFFF"
  };

  const [noticias, setNoticias] = useState<Noticia[]>([]);
  const [loading, setLoading] = useState(true);
  const [erroNoticias, setErroNoticias] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'ENEM' | 'ENADE'>('ENEM');
  const [nomeUsuario, setNomeUsuario] = useState('Usuário');
  const [avatarUri, setAvatarUri] = useState<string | null>(null);

  const carregarPerfil = async () => {
    try {
      const savedData = await AsyncStorage.getItem('@user_profile_data');
      if (savedData) {
        const data = JSON.parse(savedData);
        if (data.nome) setNomeUsuario(data.nome);
        if (data.avatarUri) setAvatarUri(data.avatarUri);
      }
    } catch (e) {
      console.error("Erro ao carregar perfil:", e);
    }
  };

  // ── Cache (TTL 4h) ──────────────────────────────────────────────────────────
  const CACHE_TTL = 4 * 60 * 60 * 1000;
  const cacheKey  = (tab: string) => `@noticias_v7_${tab}`; // v7 — com imagens do description

  const getCached = async (tab: string): Promise<Noticia[] | null> => {
    try {
      const raw = await AsyncStorage.getItem(cacheKey(tab));
      if (!raw) return null;
      const { ts, data } = JSON.parse(raw);
      // mínimo 2 itens e dentro do TTL
      if (Array.isArray(data) && data.length >= 2 && Date.now() - ts < CACHE_TTL) return data;
    } catch {}
    return null;
  };

  const saveCache = async (tab: string, data: Noticia[]) => {
    try { await AsyncStorage.setItem(cacheKey(tab), JSON.stringify({ ts: Date.now(), data })); }
    catch {}
  };

  // Imagens variadas por posição — usadas quando o feed não traz imagem própria
  const FALLBACK_IMGS = [
    'https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400', // livros/maçã
    'https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=400', // estudante escrevendo
    'https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?w=400', // biblioteca
    'https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400', // livros coloridos
    'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?w=400', // sala de aula
  ];
  const FALLBACK_IMG = FALLBACK_IMGS[0];
  const variantImg = (index: number) => FALLBACK_IMGS[index % FALLBACK_IMGS.length];

  // ── Fontes RSS por aba ────────────────────────────────────────────────────
  const RSS_SOURCES: Record<string, string[]> = {
    ENEM: [
      'https://agenciabrasil.ebc.com.br/rss/educacao/feed.rss',           // tem imagens reais
      'https://news.google.com/rss/search?q=ENEM+INEP+vestibular+prova&hl=pt-BR&gl=BR&ceid=BR:pt',
      'https://news.google.com/rss/search?q=ENEM+nota+candidatos+educacao&hl=pt-BR&gl=BR&ceid=BR:pt',
      'https://news.google.com/rss/search?q=ENEM+2024+2025+inscricao&hl=pt-BR&gl=BR&ceid=BR:pt',
    ],
    ENADE: [
      'https://agenciabrasil.ebc.com.br/rss/educacao/feed.rss',           // tem imagens reais
      'https://news.google.com/rss/search?q=ENADE+MEC+avaliacao+cursos&hl=pt-BR&gl=BR&ceid=BR:pt',
      'https://news.google.com/rss/search?q=ENADE+ensino+superior+universidade&hl=pt-BR&gl=BR&ceid=BR:pt',
      'https://news.google.com/rss/search?q=ensino+superior+MEC+universidade+Brasil&hl=pt-BR&gl=BR&ceid=BR:pt',
      'https://news.google.com/rss/search?q=ENADE+2023+2022+resultado+gabarito&hl=pt-BR&gl=BR&ceid=BR:pt',
    ],
  };

  // ── Parser RSS direto ─────────────────────────────────────────────────────
  const parseRSSXML = (xml: string, tab: string): Noticia[] => {
    const items: Noticia[] = [];
    const blocks = xml.match(/<item>([\s\S]*?)<\/item>/g) ?? [];
    for (let i = 0; i < Math.min(blocks.length, 5); i++) {
      const block = blocks[i];
      const titleMatch = block.match(/<title>(?:<!\[CDATA\[)?([\s\S]*?)(?:\]\]>)?<\/title>/);
      const titulo = titleMatch?.[1]?.trim()
        .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"') ?? '';
      if (!titulo) continue;
      const linkMatch = block.match(/<link>([\s\S]*?)<\/link>/)
        ?? block.match(/<guid[^>]*>([\s\S]*?)<\/guid>/);
      const link = linkMatch?.[1]?.trim() ?? '';
      // Tenta extrair imagem real do feed; se não tiver usa variante por posição
      const imgMatch =
        block.match(/media:content[^>]*url="([^"]+)"/)
        ?? block.match(/media:thumbnail[^>]*url="([^"]+)"/)
        ?? block.match(/enclosure[^>]*url="([^"']+)"/);
      const imagem = imgMatch?.[1] ?? variantImg(items.length);
      items.push({ titulo, link, imagem, tag: tab });
    }
    return items;
  };

  const fetchViaRSS = async (tab: string): Promise<Noticia[]> => {
    const sources = RSS_SOURCES[tab] ?? [];
    for (const rssUrl of sources) {
      try {
        const res = await fetch(rssUrl, {
          headers: { 'Accept': 'application/rss+xml, application/xml, text/xml, */*' },
        });
        if (!res.ok) continue;
        const xml = await res.text();
        const items = parseRSSXML(xml, tab);
        if (items.length >= 2) return items;
      } catch { /* próxima fonte */ }
    }
    return [];
  };

  // ── Fonte 2: GNews (reserva, 10 req/dia) ─────────────────────────────────
  const GNEWS_ENADE_QUERIES = [
    'ENADE avaliacao ensino superior',
    'ENADE universidade MEC Brasil',
    'ensino superior universidade federal Brasil',
    'ENADE resultado nota curso',
  ];

  const fetchViaGNews = async (tab: string): Promise<Noticia[]> => {
    const toNoticia = (a: any): Noticia => ({
      titulo: a.title ?? 'Notícia',
      imagem: a.image ?? FALLBACK_IMG,
      link:   a.url   ?? '',
      tag:    tab,
    });

    if (tab === 'ENEM') {
      try {
        const url = `https://gnews.io/api/v4/search?q=${encodeURIComponent('ENEM vestibular INEP Brasil')}&lang=pt&country=br&max=5&sortby=publishedAt&apikey=${GNEWS_API_KEY}`;
        const res  = await fetch(url);
        if (!res.ok) return [];
        const data = await res.json();
        if (data.errors || !data.articles?.length) return [];
        return data.articles.map(toNoticia);
      } catch { return []; }
    }

    // ENADE — percorre queries sobre ENADE/ensino superior até reunir ≥2 artigos
    const acumulado: Noticia[] = [];
    for (const q of GNEWS_ENADE_QUERIES) {
      if (acumulado.length >= 5) break;
      try {
        const url = `https://gnews.io/api/v4/search?q=${encodeURIComponent(q)}&lang=pt&country=br&max=3&apikey=${GNEWS_API_KEY}`;
        const res  = await fetch(url);
        if (!res.ok) continue;
        const data = await res.json();
        if (data.errors || !data.articles?.length) continue;
        acumulado.push(...data.articles.map(toNoticia));
      } catch { /* próxima query */ }
    }
    return acumulado.slice(0, 5);
  };

  // ── Fetch principal (cascata de fontes) ───────────────────────────────────
  const fetchNews = async (tab: 'ENEM' | 'ENADE' = activeTab, forceRefresh = false) => {
    setLoading(true);
    setErroNoticias(null);
    setNoticias([]);

    // 1. Cache válido (ignorado se forceRefresh)
    if (!forceRefresh) {
      const cached = await getCached(tab);
      if (cached) {
        setNoticias(cached);
        setLoading(false);
        return;
      }
    }

    let result: Noticia[] = [];

    // 2. RSS — fonte principal, sem quota diária
    if (!result.length) {
      try { result = await fetchViaRSS(tab); } catch {}
    }

    // 3. GNews — reserva (10 req/dia)
    if (!result.length) {
      try { result = await fetchViaGNews(tab); } catch {}
    }

    if (result.length > 0) {
      setNoticias(result);
      await saveCache(tab, result);
    } else {
      setErroNoticias('Não foi possível carregar notícias agora. Toque em Atualizar.');
    }

    setLoading(false);
  };

  // Perfil carrega ao focar a tela
  useFocusEffect(
    useCallback(() => {
      carregarPerfil();
    }, [])
  );

  // Notícias recarregam sempre que a aba muda (ou no mount)
  useEffect(() => {
    fetchNews(activeTab);
  }, [activeTab]);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} backgroundColor={theme.bg} />
      
      <ScrollView
        showsVerticalScrollIndicator={true}
        contentContainerStyle={styles.scrollContent}
        style={styles.scrollView}
      >
        
        {/* HEADER */}
        <View style={styles.header}>
          <TouchableOpacity style={[styles.notifCircle, { backgroundColor: theme.arrow }]} onPress={() => navigation.navigate('welcome')}>
            <Ionicons name="arrow-back" size={24} color={theme.icon} />
          </TouchableOpacity>

          <TouchableOpacity style={styles.userSection} onPress={() => navigation.navigate('MeusDados')}>
            <View style={styles.userInfo}>
              <Text style={[styles.greetingText, { color: theme.textSecondary }]}>BONS ESTUDOS,</Text>
              <Text style={[styles.userName, { color: theme.text }]}>{nomeUsuario}</Text>
            </View>
            
            <View style={styles.avatarWrapper}>
              {avatarUri ? (
                <Image source={{ uri: avatarUri }} style={styles.profilePic} />
              ) : (
                <View style={[styles.profilePic, styles.profilePlaceholder, { backgroundColor: theme.card }]}>
                  <MaterialCommunityIcons name="account" size={26} color="#8B5CF6" />
                </View>
              )}
            </View>
          </TouchableOpacity>
        </View>

        {/* SEÇÃO DE NOTÍCIAS */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Notícias e Avisos</Text>
          <TouchableOpacity onPress={() => fetchNews(activeTab, true)}>
            <Text style={styles.verTudo}>Atualizar</Text>
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color="#8B5CF6" />
          </View>
        ) : erroNoticias ? (
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="newspaper-variant-outline" size={40} color="#888" />
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>{erroNoticias}</Text>
          </View>
        ) : (
          <FlatList
            data={noticias}
            horizontal
            showsHorizontalScrollIndicator={false}
            keyExtractor={(_, i) => i.toString()}
            snapToAlignment="start"
            decelerationRate="fast"
            snapToInterval={width * 0.85 + 15}
            renderItem={({ item }) => (
              <TouchableOpacity style={styles.newsCard} onPress={() => Linking.openURL(item.link)}>
                <ImageBackground
                  source={{ uri: item.imagem || 'https://images.unsplash.com/photo-1588666309990-d68f08e3d4a6?w=400' }}
                  style={styles.newsImg}
                  imageStyle={{ borderRadius: 25 }}
                >
                  <View style={styles.newsOverlay}>
                    <View style={styles.badge}>
                      <Text style={styles.badgeText}>{item.tag}</Text>
                    </View>
                    <Text style={styles.newsTitle} numberOfLines={2}>{item.titulo}</Text>
                  </View>
                </ImageBackground>
              </TouchableOpacity>
            )}
          />
        )}

        {/* SELETOR ENEM/ENADE */}
        <View style={[styles.tabContainer, { backgroundColor: theme.card }]}>
          <TouchableOpacity
            style={[styles.tabBtn, activeTab === 'ENEM' && styles.tabActive]}
            onPress={() => { if (activeTab !== 'ENEM') setActiveTab('ENEM'); }}
          >
            <Text style={[styles.tabText, { color: theme.textSecondary }, activeTab === 'ENEM' && styles.tabTextActive]}>ENEM</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.tabBtn, activeTab === 'ENADE' && styles.tabActive]}
            onPress={() => { if (activeTab !== 'ENADE') setActiveTab('ENADE'); }}
          >
            <Text style={[styles.tabText, { color: theme.textSecondary }, activeTab === 'ENADE' && styles.tabTextActive]}>ENADE</Text>
          </TouchableOpacity>
        </View>

        {/* ACESSO RÁPIDO */}
        <Text style={[styles.sectionTitle, { color: theme.text }]}>Acesso Rápido</Text>
        <View style={styles.grid}>
          <MenuCard theme={theme} icon="calendar-month" title="Cronograma" sub="Sua rotina organizada" color="#4F46E5" onPress={() => navigation.navigate('Cronograma')} />
          
          <MenuCard 
            theme={theme} 
            icon="clipboard-check-outline" 
            title="Simulados" 
            sub="Pratique seus conhecimentos" 
            color="#10B981" 
            onPress={() => navigation.navigate('SimuladosDashboard')} 
          />
          
          <MenuCard 
            theme={theme}
            icon="book-open-variant" 
            title="Livros" 
            sub="Leituras recomendadas" 
            color="#F59E0B"
            onPress={() => navigation.navigate('LivrosEnade')} 
          />
          <MenuCard 
            theme={theme} 
            icon="school-outline" 
            title="Matérias" 
            sub="Conteúdo por disciplina" 
            color="#8B5CF6" 
            onPress={() => navigation.navigate('materia')} 
          />

          {/* NOVO CARD — Questões */}
          <MenuCard
            theme={theme}
            icon="help-circle-outline"
            title="Questões"
            sub="Pratique uma por vez"
            color="#EC4899"
            onPress={() => navigation.navigate('Questoes')}
          />
        </View>

      </ScrollView>

      {/* NAVBAR INFERIOR */}
      <View style={[styles.bottomNav, { backgroundColor: theme.navBg, borderTopColor: theme.border }]}>
        <NavButton theme={theme} icon="home-variant" label="Início" active onPress={() => navigation.navigate('welcome')} />
        <NavButton theme={theme} icon="book-open-outline" label="Matérias" onPress={() => navigation.navigate('materia')} />
        <NavButton theme={theme} icon="clipboard-text-outline" label="Simulados" onPress={() => navigation.navigate('SimuladosDashboard')} />
        <NavButton theme={theme} icon="account-outline" label="Perfil" onPress={() => navigation.navigate('MeusDados')} />
      </View>
    </SafeAreaView>
  );
}

const MenuCard = ({ icon, title, sub, color, onPress, theme }: any) => (
  <TouchableOpacity style={[styles.card, { backgroundColor: theme.card }]} onPress={onPress}>
    <View style={[styles.iconBox, { backgroundColor: `${color}15` }]}>
      <MaterialCommunityIcons name={icon} size={24} color={color} />
    </View>
    <Text style={[styles.cardTitle, { color: theme.text }]}>{title}</Text>
    <Text style={[styles.cardSub, { color: theme.textSecondary }]}>{sub}</Text>
  </TouchableOpacity>
);

const NavButton = ({ icon, label, active, onPress, theme }: any) => (
  <TouchableOpacity style={styles.navItem} onPress={onPress}>
    <MaterialCommunityIcons name={icon} size={26} color={active ? "#8B5CF6" : theme.icon} />
    <Text style={[styles.navLabel, { color: active ? "#8B5CF6" : theme.icon }]}>{label}</Text>
  </TouchableOpacity>
);

const styles = StyleSheet.create({
  container: { flex: 1, ...(Platform.OS === 'web' ? { height } : {}) }, 
  scrollView: { flex: 1, ...(Platform.OS === 'web' ? { height, overflow: 'scroll' as any } : {}) },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 160 },
 header: {flexDirection: 'row', justifyContent: 'space-between',alignItems: 'center', marginTop: Platform.OS === 'android' ? (StatusBar.currentHeight || 0) + 15 : 10, marginBottom: 25 },
  notifCircle: { width: 45, height: 45, borderRadius: 23, justifyContent: 'center', alignItems: 'center' },
  userSection: { flexDirection: 'row', alignItems: 'center' },
  userInfo: { marginRight: 12, alignItems: 'flex-end' },
  greetingText: { fontSize: 10, fontWeight: 'bold' },
  userName: { fontSize: 16, fontWeight: 'bold' },
  avatarWrapper: { borderRadius: 23, borderWidth: 2, borderColor: '#8B5CF6', padding: 2 },
  profilePic: { width: 40, height: 40, borderRadius: 20 },
  profilePlaceholder: { justifyContent: 'center', alignItems: 'center' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 15, alignItems: 'center' },
  sectionTitle: { fontSize: 20, fontWeight: 'bold' },
  verTudo: { color: '#8B5CF6', fontWeight: 'bold' },
  loaderContainer: { height: 210, justifyContent: 'center', alignItems: 'center' },
  emptyContainer: { height: 210, justifyContent: 'center', alignItems: 'center', gap: 10 },
  emptyText: { fontSize: 13, textAlign: 'center', paddingHorizontal: 20 },
  newsCard: { width: width * 0.85, height: 210, marginRight: 15 },
  newsImg: { flex: 1, justifyContent: 'flex-end' },
  newsOverlay: { padding: 20, backgroundColor: 'hsla(0, 0%, 0%, 0.50)', borderBottomLeftRadius: 25, borderBottomRightRadius: 25 },
  badge: { backgroundColor: '#8B5CF6', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, alignSelf: 'flex-start', marginBottom: 8 },
  badgeText: { color: '#FFF', fontSize: 10, fontWeight: 'bold' },
  newsTitle: { color: '#FFF', fontSize: 16, fontWeight: 'bold' },
  tabContainer: { flexDirection: 'row', borderRadius: 16, padding: 6, marginVertical: 25 },
  tabBtn: { flex: 1, paddingVertical: 14, alignItems: 'center', borderRadius: 12 },
  tabActive: { backgroundColor: '#8B5CF6' },
  tabText: { fontWeight: 'bold', fontSize: 14 },
  tabTextActive: { color: '#FFF' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', marginTop: 10 },
  card: { width: '48%', padding: 20, borderRadius: 28, marginBottom: 15, minHeight: 165 },
  iconBox: { width: 48, height: 48, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  cardTitle: { fontSize: 16, fontWeight: 'bold' },
  cardSub: { fontSize: 11, marginTop: 4 },
  bottomNav: { position: 'absolute', bottom: 0, width: width, flexDirection: 'row', justifyContent: 'space-around', paddingVertical: 15, borderTopWidth: 0.5 },
  navItem: { alignItems: 'center' },
  navLabel: { fontSize: 10, marginTop: 5 }
});
