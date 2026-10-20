import React, { useState, useEffect, useCallback, useRef } from 'react';
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
import {
  buscarViaProxy, buscarViaRSS, rssDiretoFunciona,
  lerCache, gravarCache,
  type Noticia, type AbaNoticia,
} from '../../services/noticiasService';
import { useTheme } from '../TemasAcoes/Temas';

const { width, height } = Dimensions.get('window');

export default function EnemEnadePage() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const theme = {
    bg: isDarkMode ? "#000000" : "#F5F5F7",
    card: isDarkMode ? "#15151C" : "#FFFFFF",
    arrow: isDarkMode ? "#16161A"  : "#EAEAEA",
    text: isDarkMode ? "#FFFFFF" : "#333333",
    textSecondary: isDarkMode ? "#858585" : "#707070",   // 3.16/2.85 → 4.73/4.67
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

  // ── Notícias ───────────────────────────────────────────────────────────────
  // A busca, a junção das fontes e o cache moram em noticiasService.ts.
  // Aqui fica só o estado da tela.
  // Cada busca recebe um número. Só a MAIS RECENTE tem permissão de
  // escrever no estado — sem isso, trocar de aba enquanto a anterior ainda
  // busca faz a resposta atrasada sobrescrever a lista da aba nova.
  const buscaAtual = useRef(0);

  const fetchNews = async (tab: AbaNoticia = activeTab, forceRefresh = false) => {
    const minhaBusca = ++buscaAtual.current;
    const souAtual = () => minhaBusca === buscaAtual.current;

    setLoading(true);
    setErroNoticias(null);
    setNoticias([]);

    if (!forceRefresh) {
      const cached = await lerCache(tab);
      if (cached) {
        if (!souAtual()) return;
        setNoticias(cached);
        setLoading(false);
        return;
      }
    }

    let result: Noticia[] = [];

    // 1. noticias_api.py — busca do lado do servidor, com CORS liberado e
    //    cache de 8 h. É o único caminho que funciona no navegador, e o
    //    que poupa a cota do GNews.
    try { result = await buscarViaProxy(tab); } catch {}

    // 2. RSS direto — só no celular. No navegador é bloqueado por CORS
    //    antes da resposta chegar, então nem vale a tentativa.
    if (!result.length && rssDiretoFunciona) {
      try { result = await buscarViaRSS(tab); } catch {}
    }

    // Aqui havia um degrau 3: chamar o GNews DIRETO do aplicativo, com a
    // chave vinda do .env e empacotada no aplicativo publicado.
    //
    // Chave que vai no pacote é chave pública: qualquer pessoa extrai do
    // APK, e a cota — que é sua — passa a ser de quem achar. Não existe
    // jeito de embutir segredo em cliente; o que existe é não embutir.
    //
    // O GNews continua sendo usado, só que do outro lado: o
    // noticias_api.py o chama com a chave que mora numa variável de
    // ambiente do servidor, e o aplicativo fala com o servidor (degrau 1).
    // De quebra, o cache de 8 h de lá serve todo mundo com uma consulta só,
    // em vez de cada aparelho gastar a sua.

    if (result.length > 0) {
      await gravarCache(tab, result);   // o cache vale para a aba, atrasada ou não
      if (!souAtual()) return;
      setNoticias(result);
    } else {
      if (!souAtual()) return;
      setErroNoticias(
        rssDiretoFunciona
          ? 'Não foi possível carregar notícias agora. Toque em Atualizar.'
          // Antes esta mensagem mandava o usuário rodar
          // `uvicorn noticias_api:app --port 8000`. Ninguém que baixou um
          // aplicativo de estudos vai abrir um terminal.
          : 'Não foi possível carregar as notícias agora. Toque em Atualizar.',
      );
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
          <TouchableOpacity style={[styles.notifCircle, { backgroundColor: theme.arrow }]} onPress={() => navigation.navigate('welcome')}
            accessibilityRole="button"
            accessibilityLabel="Voltar"
          >
            <Ionicons name="arrow-back" size={24} color={theme.icon} />
          </TouchableOpacity>

          <TouchableOpacity accessibilityRole="button" style={styles.userSection} onPress={() => navigation.navigate('MeusDados')}>
            <View style={styles.userInfo}>
              <Text style={[styles.greetingText, { color: theme.textSecondary }]}>BONS ESTUDOS,</Text>
              <Text style={[styles.userName, { color: theme.text }]}>{nomeUsuario}</Text>
            </View>
            
            <View style={styles.avatarWrapper}>
              {avatarUri ? (
                <Image source={{ uri: avatarUri }} style={styles.profilePic} />
              ) : (
                <View style={[styles.profilePic, styles.profilePlaceholder, { backgroundColor: theme.card }]}>
                  <MaterialCommunityIcons name="account" size={26} color="#7D53DD" />
                </View>
              )}
            </View>
          </TouchableOpacity>
        </View>

        {/* SEÇÃO DE NOTÍCIAS */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Notícias e Avisos</Text>
          <TouchableOpacity accessibilityRole="button" onPress={() => fetchNews(activeTab, true)}>
            <Text style={[styles.verTudo, { color: isDarkMode ? '#9775E4' : '#7D53DD' }]}>Atualizar</Text>
          </TouchableOpacity>
        </View>

        {loading ? (
          <View style={styles.loaderContainer}>
            <ActivityIndicator size="large" color="#7D53DD" />
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
              <TouchableOpacity accessibilityRole="button" style={styles.newsCard} onPress={() => Linking.openURL(item.link)}>
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
          <TouchableOpacity accessibilityRole="button"
            style={[styles.tabBtn, activeTab === 'ENEM' && styles.tabActive]}
            onPress={() => { if (activeTab !== 'ENEM') setActiveTab('ENEM'); }}
          >
            <Text style={[styles.tabText, { color: theme.textSecondary }, activeTab === 'ENEM' && styles.tabTextActive]}>ENEM</Text>
          </TouchableOpacity>
          <TouchableOpacity accessibilityRole="button"
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
            color="#7D53DD" 
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
  <TouchableOpacity accessibilityRole="button" style={[styles.card, { backgroundColor: theme.card }]} onPress={onPress}>
    <View style={[styles.iconBox, { backgroundColor: `${color}15` }]}>
      <MaterialCommunityIcons name={icon} size={24} color={color} />
    </View>
    <Text style={[styles.cardTitle, { color: theme.text }]}>{title}</Text>
    <Text style={[styles.cardSub, { color: theme.textSecondary }]}>{sub}</Text>
  </TouchableOpacity>
);

const NavButton = ({ icon, label, active, onPress, theme }: any) => (
  <TouchableOpacity accessibilityRole="button" style={styles.navItem} onPress={onPress}>
    <MaterialCommunityIcons name={icon} size={26} color={active ? "#7D53DD" : theme.icon} />
    <Text style={[styles.navLabel, { color: active ? "#7D53DD" : theme.icon }]}>{label}</Text>
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
  avatarWrapper: { borderRadius: 23, borderWidth: 2, borderColor: '#7D53DD', padding: 2 },
  profilePic: { width: 40, height: 40, borderRadius: 20 },
  profilePlaceholder: { justifyContent: 'center', alignItems: 'center' },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 15, alignItems: 'center' },
  sectionTitle: { fontSize: 20, fontWeight: 'bold' },
  verTudo: { color: '#7D53DD', fontWeight: 'bold' },
  loaderContainer: { height: 210, justifyContent: 'center', alignItems: 'center' },
  emptyContainer: { height: 210, justifyContent: 'center', alignItems: 'center', gap: 10 },
  emptyText: { fontSize: 13, textAlign: 'center', paddingHorizontal: 20 },
  newsCard: { width: width * 0.85, height: 210, marginRight: 15 },
  newsImg: { flex: 1, justifyContent: 'flex-end' },
  newsOverlay: { padding: 20, backgroundColor: 'hsla(0, 0%, 0%, 0.50)', borderBottomLeftRadius: 25, borderBottomRightRadius: 25 },
  badge: { backgroundColor: '#7D53DD', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 8, alignSelf: 'flex-start', marginBottom: 8 },
  badgeText: { color: '#FFF', fontSize: 10, fontWeight: 'bold' },
  newsTitle: { color: '#FFF', fontSize: 16, fontWeight: 'bold' },
  tabContainer: { flexDirection: 'row', borderRadius: 16, padding: 6, marginVertical: 25 },
  tabBtn: { flex: 1, paddingVertical: 14, alignItems: 'center', borderRadius: 12 },
  tabActive: { backgroundColor: '#7D53DD' },
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