import React, { useState, useEffect } from 'react';
import { 
  StyleSheet, 
  Text, 
  View, 
  Image, 
  TouchableOpacity, 
  TextInput,
  ScrollView,
  StatusBar,
  Linking
} from 'react-native';
import { Ionicons, FontAwesome5 } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// IMPORTAÇÃO DO TEMA GLOBAL (Ajuste o caminho conforme seu projeto)
import { useTheme } from '../../pages/TemasAcoes/Temas'; 

// DADOS MOCKADOS ATUALIZADOS COM NOVOS CONCURSOS E LINKS
const DADOS_CONCURSOS = [
  {
    id: '1',
    nome: 'Caixa Econômica',
    cargo: 'Técnico Bancário',
    vagas: '4.000 + CR',
    salario: 'R$ 3.762,00',
    corLogo: '#2563EB', // Azul Caixa
    textoLogo: 'CAIXA',
    corTextoLogo: '#FFFFFF',
    status: 'ABERTOS',
    link: 'https://caixa.gov.br/sobre-a-caixa/trabalhe-na-caixa/Paginas/default.aspx'
  },
  {
    id: '2',
    nome: 'Correios',
    cargo: 'Agente e Analista',
    vagas: '3.449',
    salario: 'R$ 2.429,00',
    corLogo: '#FACC15', // Amarelo Correios
    textoLogo: 'CORREIOS',
    corTextoLogo: '#000000',
    status: 'ENCERRADOS',
    link: ''
  },
  {
    id: '3',
    nome: 'Banco do Brasil',
    cargo: 'Agente Comercial',
    vagas: '6.000',
    salario: 'R$ 3.622,23',
    corLogo: '#FDE047', // Amarelo BB
    textoLogo: 'BB',
    corTextoLogo: '#0038A8', // Azul BB
    status: 'PREVISTOS',
    link: 'https://www.bb.com.br/site/concurso-bb/'
  },
  {
    id: '4',
    nome: 'INSS',
    cargo: 'Técnico do Seguro Social',
    vagas: '1.000',
    salario: 'R$ 5.905,79',
    corLogo: '#005C94', // Azul Gov.br
    textoLogo: 'INSS',
    corTextoLogo: '#FFFFFF',
    status: 'ENCERRADOS',
    link: '' // Propositalmente sem link
  },
  {
    id: '5',
    nome: 'Petrobras',
    cargo: 'Nível Técnico e Superior',
    vagas: '6.412',
    salario: 'R$ 5.878,82',
    corLogo: '#008542', // Verde Petrobras
    textoLogo: 'BR',
    corTextoLogo: '#FCD116', // Amarelo Petrobras
    status: 'ABERTOS',
    link: 'https://petrobras.com.br/quem-somos/carreiras/concursos'
  },
];

const FILTROS = ['ABERTOS', 'PREVISTOS', 'ENCERRADOS'];

export default function ConcursosScreen() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [nomeUsuario, setNomeUsuario] = useState('Usuário');
  const [avatarUri, setAvatarUri] = useState<string | null>(null);
  const [busca, setBusca] = useState('');
  const [filtroAtivo, setFiltroAtivo] = useState('ABERTOS');

  // Cores dinâmicas para modo claro e escuro baseadas no tema
  const theme = {
    bg: isDarkMode ? "#000000" : "#F5F5F7",
    card: isDarkMode ? "#121214" : "#FFFFFF",
    cardSecondary: isDarkMode ? "#202024" : "#F0F0F0",
    text: isDarkMode ? "#FFFFFF" : "#1A1A1A",
    textSecondary: isDarkMode ? "#8C8C8C" : "#707070",   // 3.26 → 4.6+
    border: isDarkMode ? "#29292E" : "#E5E5E5",
    iconBg: isDarkMode ? "#202024" : "#E0E0E0",
    primary: "#6B21A8", 
    primaryLight: "#7D53DD", 
  };

  useEffect(() => {
    const carregarPerfil = async () => {
      try {
        const savedData = await AsyncStorage.getItem('@user_profile_data');
        if (savedData) {
          const data = JSON.parse(savedData);
          setNomeUsuario(data.nome || "Kayron");
          setAvatarUri(data.avatarUri || null);
        }
      } catch (e) { console.log(e); }
    };
    carregarPerfil();
  }, []);

  // Filtragem dos concursos
  const concursosFiltrados = DADOS_CONCURSOS.filter(concurso => {
    const matchBusca = concurso.nome.toLowerCase().includes(busca.toLowerCase()) || 
                       concurso.cargo.toLowerCase().includes(busca.toLowerCase());
    const matchFiltro = concurso.status === filtroAtivo;
    return matchBusca && matchFiltro;
  });

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />

      {/* CABEÇALHO PADRÃO DO APLICATIVO */}
      <View style={styles.header}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} 
          onPress={() => navigation.goBack()} 
          style={[styles.iconButton, { backgroundColor: theme.iconBg }]}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color={theme.text} />          
        </TouchableOpacity>

        <TouchableOpacity accessibilityRole="button" 
          style={styles.rowCenter} 
          onPress={() => navigation.navigate('MeusDados')}
          activeOpacity={0.7}
        >
          <View style={styles.userInfo}>
            <Text style={[styles.greetingText, { color: isDarkMode ? '#8C8C8C' : '#707070' }]}>BONS ESTUDOS,</Text>
            <Text style={[styles.userName, { color: theme.text }]}>{nomeUsuario}</Text>
          </View>
          {avatarUri ? (
            <Image source={{ uri: avatarUri }} style={styles.profilePic} />
          ) : (
            <View style={[styles.profilePic, styles.profilePlaceholder, { backgroundColor: theme.iconBg }]}>
              <FontAwesome5 name="user-alt" size={18} color={theme.primaryLight} />
            </View>
          )}
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollPadding}>
        
        {/* TÍTULO DA TELA */}
        <Text style={[styles.screenTitle, { color: theme.text }]}>Concursos Brasil</Text>

        {/* BARRA DE BUSCA */}
        <View style={[styles.searchBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
          <Ionicons name="search" size={20} color={theme.textSecondary} />
          <TextInput 
            placeholder="Buscar concursos..." 
            placeholderTextColor={theme.textSecondary}
            style={[styles.searchInput, { color: theme.text }]}
            value={busca}
            onChangeText={setBusca}
          />
        </View>

        {/* CHIPS DE FILTRO (ABERTOS, PREVISTOS, ENCERRADOS) */}
        <ScrollView 
          horizontal 
          showsHorizontalScrollIndicator={false} 
          style={styles.chipsContainer}
          contentContainerStyle={{ paddingRight: 20 }}
        >
          {FILTROS.map((filtro) => {
            const isAtivo = filtroAtivo === filtro;
            return (
              <TouchableOpacity accessibilityRole="button"
                key={filtro}
                style={[
                  styles.chip,
                  { backgroundColor: isAtivo ? theme.primaryLight : theme.cardSecondary }
                ]}
                onPress={() => setFiltroAtivo(filtro)}
                activeOpacity={0.7}
              >
                <Text style={[
                  styles.chipText,
                  { color: isAtivo ? '#FFFFFF' : theme.textSecondary }
                ]}>
                  {filtro}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>

        {/* SEÇÃO DE DESTAQUES */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: theme.text }]}>Destaques</Text>
          <TouchableOpacity accessibilityRole="button">
            <Text style={[styles.seeAllText, { color: theme.primaryLight }]}>Ver tudo</Text>
          </TouchableOpacity>
        </View>

        {/* LISTA DE CARDS DE CONCURSOS */}
        <View style={styles.listContainer}>
          {concursosFiltrados.length > 0 ? (
            concursosFiltrados.map((concurso) => (
              <View 
                key={concurso.id} 
                style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}
              >
                {/* CABEÇALHO DO CARD (Logo, Título e Subtítulo) */}
                <View style={styles.cardHeader}>
                  <View style={[styles.logoBox, { backgroundColor: concurso.corLogo }]}>
                    <Text style={[styles.logoText, { color: concurso.corTextoLogo }]} numberOfLines={1}>
                      {concurso.textoLogo}
                    </Text>
                  </View>
                  <View style={styles.cardHeaderInfo}>
                    <Text style={[styles.cardTitle, { color: theme.text }]}>{concurso.nome}</Text>
                    <Text style={[styles.cardSubtitle, { color: theme.textSecondary }]}>{concurso.cargo}</Text>
                  </View>
                </View>

                {/* INFORMAÇÕES DE VAGAS E SALÁRIO */}
                <View style={styles.infoRow}>
                  <View style={styles.infoBlock}>
                    <Text style={[styles.infoLabel, { color: isDarkMode ? '#8C8C8C' : '#707070' }]}>VAGAS</Text>
                    <Text style={[styles.infoValue, { color: theme.text }]}>{concurso.vagas}</Text>
                  </View>
                  <View style={styles.infoBlock}>
                    <Text style={[styles.infoLabel, { color: isDarkMode ? '#8C8C8C' : '#707070' }]}>SALÁRIO</Text>
                    <Text style={[styles.infoValue, { color: theme.text }]}>{concurso.salario}</Text>
                  </View>
                </View>

                {/* BOTÕES DE AÇÕES SECUNDÁRIAS */}
                <View style={styles.actionRow}>
                  <TouchableOpacity accessibilityRole="button" 
                    style={[styles.actionBtnSecondary, { backgroundColor: theme.cardSecondary }]}
                    onPress={() => concurso.link ? Linking.openURL(concurso.link) : null}
                  >
                    <Text style={[styles.actionBtnTextSecondary, { color: theme.text }]}>Detalhes</Text>
                  </TouchableOpacity>
                  <TouchableOpacity accessibilityRole="button" style={[styles.actionBtnSecondary, { backgroundColor: theme.cardSecondary }]}>
                    <Text style={[styles.actionBtnTextSecondary, { color: theme.text }]}>Provas</Text>
                  </TouchableOpacity>
                  <TouchableOpacity accessibilityRole="button" style={[styles.actionBtnSecondary, { backgroundColor: theme.cardSecondary }]}>
                    <Text style={[styles.actionBtnTextSecondary, { color: theme.text }]}>Simulados</Text>
                  </TouchableOpacity>
                </View>

                {/* BOTÃO PRINCIPAL "ESTUDAR" */}
                <TouchableOpacity accessibilityRole="button" 
                  style={[styles.mainActionBtn, { backgroundColor: theme.primaryLight }]}
                  activeOpacity={0.8}
                  onPress={() => concurso.link ? Linking.openURL(concurso.link) : null}
                >
                  <Text style={styles.mainActionText}>ESTUDAR</Text>
                </TouchableOpacity>
              </View>
            ))
          ) : (
            <Text style={{ color: theme.textSecondary, textAlign: 'center', marginTop: 30 }}>
              Nenhum concurso encontrado.
            </Text>
          )}
        </View>

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollPadding: { paddingBottom: 50 },
  
  // Header Perfil
  header: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    alignItems: 'center', 
    marginTop: 60, 
    marginBottom: 10,
    paddingHorizontal: 20 
  },
  rowCenter: { flexDirection: 'row', alignItems: 'center' },
  userInfo: { marginRight: 10, alignItems: 'flex-end' },
  greetingText: { fontSize: 10, fontWeight: 'bold' },
  userName: { fontSize: 16, fontWeight: 'bold' },
  profilePic: { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: '#7D53DD' },
  profilePlaceholder: { justifyContent: 'center', alignItems: 'center' },
  iconButton: { padding: 10, borderRadius: 50 },

  // Título da Tela
  screenTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    marginHorizontal: 20,
    marginBottom: 20,
  },

  // Busca
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 20,
    paddingHorizontal: 15,
    height: 50,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 20
  },
  searchInput: { flex: 1, marginLeft: 10, fontSize: 15 },

  // Filtros (Chips)
  chipsContainer: {
    paddingLeft: 20,
    marginBottom: 25,
    maxHeight: 45,
  },
  chip: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 20,
    marginRight: 10,
    justifyContent: 'center',
    alignItems: 'center',
    height: 40,
  },
  chipText: {
    fontSize: 13,
    fontWeight: 'bold',
  },

  // Destaques (Section)
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  seeAllText: {
    fontSize: 14,
    fontWeight: '500',
  },

  // Lista de Cards
  listContainer: {
    paddingHorizontal: 20,
  },
  card: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 18,
    marginBottom: 15,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
  },
  logoBox: {
    width: 65,
    height: 65,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 15,
  },
  logoText: {
    fontWeight: 'bold',
    fontSize: 11,
    letterSpacing: 0.5,
  },
  cardHeaderInfo: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 14,
  },

  // Info Row (Vagas e Salário)
  infoRow: {
    flexDirection: 'row',
    marginBottom: 20,
  },
  infoBlock: {
    marginRight: 40,
  },
  infoLabel: {
    // cor definida no uso, por tema
    fontSize: 10,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 15,
    fontWeight: 'bold',
  },

  // Botões de Ação Secundários
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 15,
  },
  actionBtnSecondary: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginHorizontal: 4,
  },
  actionBtnTextSecondary: {
    fontSize: 13,
    fontWeight: '500',
  },

  // Botão Principal
  mainActionBtn: {
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 5,
  },
  mainActionText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 0.5,
  }
});