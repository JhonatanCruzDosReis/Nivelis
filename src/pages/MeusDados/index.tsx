import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, Image, TextInput, TouchableOpacity, StatusBar,
  ScrollView, KeyboardAvoidingView, Platform, Modal, ActivityIndicator
} from 'react-native';
import { MaterialIcons, Feather, Ionicons } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import * as ImagePicker from 'expo-image-picker';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useTheme } from '../TemasAcoes/Temas';
import { styles } from './styles';
import NivelisModal, { useNivelisModal } from '../../components/NivelisModal';
import {
  carregarEstatisticasPorMateria,
  carregarHistorico,
  getMateriaCor,
  limparDesempenho,
  type MateriaStats,
} from '../../services/desempenhoService';
import { limparHistoricoQuestoes } from '../../services/questoesService';
import { questoesFeitasApi } from '../../services/apiService';
import { auth } from '../../services/firebase';

export default function ProfileData() {
  const navigation = useNavigation<any>();
  const { isDarkMode, toggleTheme } = useTheme();
  const { modal, showModal } = useNivelisModal();

  // ── APAGAR HISTÓRICO ──────────────────────────────────────────────────────
  //
  // As três funções de limpeza existiam no código e NENHUMA tela as chamava,
  // então não havia como o usuário zerar o próprio histórico. Pior: o
  // simulado de demonstração gravava desempenho, e quem explorou os cards de
  // exemplo ficava com eles somados para sempre.
  //
  // Apaga as três coisas juntas de propósito. Zerar só o desempenho e deixar
  // a memória de questões feitas produz o pior dos mundos: o histórico diz
  // que você nunca estudou, e as questões continuam sem aparecer porque
  // seguem marcadas como feitas.
  const apagarHistorico = () => {
    showModal(
      'Apagar seu histórico?',
      'Isto remove suas sessões de estudo, as estatísticas de desempenho e a '
      + 'memória de quais questões você já fez. As questões voltam a aparecer '
      + 'como novas. Não dá para desfazer.',
      'warning',
      [
        { text: 'Cancelar', style: 'secondary', onPress: () => {} },
        { text: 'Apagar tudo', style: 'danger', onPress: async () => {
            const uid = auth.currentUser?.uid ?? 'anonimo';
            // Em sequência, e com erro individual tolerado: se uma falhar, as
            // outras ainda limpam, e o usuário sabe o que sobrou.
            const falhas: string[] = [];
            try { await limparDesempenho(); }        catch { falhas.push('desempenho'); }
            try { await limparHistoricoQuestoes(); } catch { falhas.push('sessões'); }
            try { await questoesFeitasApi.limpar(uid); } catch { falhas.push('questões feitas'); }

            setMenuVisible(false);
            if (falhas.length === 0) {
              // Zera o que está na tela agora, para o usuário ver o efeito
              // sem precisar sair e voltar.
              setPorMateria({});
              setTotalGeral({ acertos: 0, total: 0, provas: 0 });
              showModal('Histórico apagado',
                        'Tudo zerado. As questões voltam a aparecer como novas.',
                        'success');
            } else {
              showModal('Apagado em parte',
                        `Não deu para limpar: ${falhas.join(', ')}. `
                        + 'Tente de novo com internet.',
                        'error');
            }
          } },
      ],
    );
  };

  const [nome,      setNome]      = useState('');
  const [dataNasc,  setDataNasc]  = useState('');
  const [celular,   setCelular]   = useState('');
  const [email,     setEmail]     = useState('');
  const [avatarUri, setAvatarUri] = useState<string | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [menuVisible, setMenuVisible] = useState(false);

  // Desempenho: o serviço já vinha gravando acertos a cada simulado
  // entregue, mas nada nesta tela lia esses números.
  const [porMateria, setPorMateria] = useState<Record<string, MateriaStats>>({});
  const [totalGeral, setTotalGeral] = useState({ acertos: 0, total: 0, provas: 0 });
  const [carregandoDesempenho, setCarregandoDesempenho] = useState(true);

  const defaultUserIcon = 'https://cdn-icons-png.flaticon.com/512/149/149071.png';

  const theme = {
    bg:         isDarkMode ? "#12121b" : "#F5F5F7",
    card:       isDarkMode ? "#1e1e2d" : "#FFFFFF",
    text:       isDarkMode ? "#FFFFFF" : "#333333",
    inputLabel: isDarkMode ? "#CCC"    : "#6A6A6A",
    border:     isDarkMode ? "#444"    : "#DDD",
    icon:       isDarkMode ? "#CCC"    : "#999",
  };

  useEffect(() => { loadUserData(); }, []);

  // Recarrega ao voltar para a tela: quem acabou de entregar um
  // simulado espera ver o número já atualizado aqui.
  useFocusEffect(
    useCallback(() => {
      let vivo = true;
      (async () => {
        try {
          const [stats, historico] = await Promise.all([
            carregarEstatisticasPorMateria(),
            carregarHistorico(),
          ]);
          if (!vivo) return;
          setPorMateria(stats);
          setTotalGeral({
            acertos: historico.reduce((s, h) => s + h.acertos, 0),
            total:   historico.reduce((s, h) => s + h.total, 0),
            provas:  historico.length,
          });
        } catch {
          // Desempenho é complemento: se falhar, a tela de dados
          // continua servindo para o que ela já servia.
        } finally {
          if (vivo) setCarregandoDesempenho(false);
        }
      })();
      return () => { vivo = false; };
    }, [])
  );

  const loadUserData = async () => {
    try {
      const raw = await AsyncStorage.getItem('@user_profile_data');
      if (raw) {
        const data = JSON.parse(raw);
        setNome(data.nome || '');
        setDataNasc(data.dataNasc || '');
        setCelular(data.celular || '');
        setEmail(data.email || '');
        setAvatarUri(data.avatarUri || null);
      }
    } catch {
      showModal('Erro', 'Não foi possível carregar os dados.', 'error');
    }
  };

  const handleSaveData = async () => {
    if (!nome.trim()) {
      showModal('Atenção', 'O nome não pode estar vazio.', 'warning');
      return;
    }
    setLoading(true);
    try {
      const userData = { nome, dataNasc, celular, email, avatarUri };
      await AsyncStorage.setItem('@user_profile_data', JSON.stringify(userData));
      showModal('Salvo! ✅', 'Seus dados foram atualizados com sucesso.', 'success');
    } catch {
      showModal('Erro', 'Não foi possível salvar os dados.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleEditPhoto = async () => {
    const { status } = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (status !== 'granted') {
      showModal('Permissão negada', 'Habilite o acesso à galeria nas configurações do dispositivo.', 'warning');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.7,
    });
    if (!result.canceled) setAvatarUri(result.assets[0].uri);
  };

  // --- NOVA FUNÇÃO PARA REMOVER FOTO ---
  const handleRemovePhoto = () => {
    setAvatarUri(null);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={[styles.container, { backgroundColor: theme.bg }]}
    >
      <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />

      {/* MODAL DO MENU */}
      <Modal
        transparent
        visible={menuVisible}
        animationType="slide"
        onRequestClose={() => setMenuVisible(false)}
      >
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setMenuVisible(false)}>
          <TouchableOpacity activeOpacity={1} style={[styles.menuContainer, { backgroundColor: theme.card }]}>
            <View style={styles.dragIndicator} />

            <TouchableOpacity accessibilityRole="button" style={styles.menuItem} onPress={() => { toggleTheme(); setMenuVisible(false); }}>
              <Feather name={isDarkMode ? "sun" : "moon"} size={22} color={theme.text} />
              <Text style={[styles.menuText, { color: theme.text }]}>
                Modo {isDarkMode ? "claro" : "escuro"}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.menuItem}
              onPress={apagarHistorico}
              accessibilityRole="button"
              accessibilityLabel="Apagar meu histórico de estudos"
            >
              <Feather name="trash-2" size={22} color={theme.text} />
              <Text style={[styles.menuText, { color: theme.text }]}>
                Apagar meu histórico
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.menuItem}
              onPress={() => { setMenuVisible(false); navigation.navigate('Login'); }}
              accessibilityRole="button"
              accessibilityLabel="Sair da conta"
            >
              <Feather name="power" size={22} color="#ff4444" />
              <Text style={[styles.menuText, { color: '#ff4444' }]}>Sair</Text>
            </TouchableOpacity>

            <Text style={styles.versionText}>Versão do app: 1.40.0</Text>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>

      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <MaterialIcons name="arrow-back" size={28} color={theme.text} />
        </TouchableOpacity>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => setMenuVisible(true)}
          accessibilityRole="button"
          accessibilityLabel="Mais opções"
        >
          <MaterialIcons name="more-vert" size={28} color={theme.text} />
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
        
        {/* FOTO E AÇÕES */}
        <View style={styles.profileSection}>
          <View style={styles.avatarWrapper}>
            <View style={[styles.avatarContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
              <Image source={{ uri: avatarUri ?? defaultUserIcon }} style={styles.avatar} />
            </View>
          </View>

          {/* NOVOS BOTÕES DE EDITAR E EXCLUIR */}
          <View style={{ flexDirection: 'row', justifyContent: 'center', marginTop: 15, marginBottom: 5 }}>
            
            <TouchableOpacity accessibilityRole="button" 
              onPress={handleEditPhoto} 
              activeOpacity={0.8}
              style={{
                flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
                backgroundColor: isDarkMode ? '#2a2a3d' : '#E0E0E0',
                paddingVertical: 8, paddingHorizontal: 15, borderRadius: 20, width: 110,
                marginHorizontal: 5
              }}
            >
              <Ionicons name="camera" size={16} color={theme.text} />
              <Text style={{ color: theme.text, marginLeft: 6, fontWeight: '600', fontSize: 13 }}>Editar</Text>
            </TouchableOpacity>

            {avatarUri && (
              <TouchableOpacity accessibilityRole="button" 
                onPress={handleRemovePhoto} 
                activeOpacity={0.8}
                style={{
                  flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
                  backgroundColor: isDarkMode ? 'rgba(255, 68, 68, 0.15)' : '#FFEBEB',
                  borderWidth: 1, borderColor: '#ff4444',
                  paddingVertical: 8, paddingHorizontal: 15, borderRadius: 20, width: 110,
                  marginHorizontal: 5
                }}
              >
                <Ionicons name="trash" size={16} color="#ff4444" />
                <Text style={{ color: '#ff4444', marginLeft: 6, fontWeight: '600', fontSize: 13 }}>Excluir</Text>
              </TouchableOpacity>
            )}

          </View>

          <Text style={[styles.userName, { color: theme.text, marginTop: 10 }]}>{nome || 'Novo Usuário'}</Text>
        </View>

        {/* DESEMPENHO */}
        <View style={styles.formSection}>
          <Text style={[styles.sectionTitle, { color: isDarkMode ? '#9775E4' : '#7D53DD' }]}>Meu desempenho</Text>

          {carregandoDesempenho ? (
            <View style={{ paddingVertical: 24, alignItems: 'center' }}>
              <ActivityIndicator color={theme.icon} />
            </View>
          ) : totalGeral.total === 0 ? (
            <View style={[{
              backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1,
              borderRadius: 12, padding: 18, alignItems: 'center',
            }]}>
              <MaterialIcons name="insights" size={28} color={theme.icon} />
              <Text style={{ color: theme.inputLabel, marginTop: 8, textAlign: 'center' }}>
                Você ainda não entregou nenhum simulado. Seus acertos aparecem aqui
                assim que terminar o primeiro.
              </Text>
            </View>
          ) : (
            <>
              {/* Resumo geral */}
              <View style={{
                backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1,
                borderRadius: 12, padding: 16, flexDirection: 'row',
                justifyContent: 'space-around', alignItems: 'center',
              }}>
                <View style={{ alignItems: 'center' }}>
                  <Text style={{ color: theme.text, fontSize: 26, fontWeight: '700' }}>
                    {totalGeral.acertos}
                    <Text style={{ color: theme.inputLabel, fontSize: 16, fontWeight: '500' }}>
                      {` / ${totalGeral.total}`}
                    </Text>
                  </Text>
                  <Text style={{ color: theme.inputLabel, fontSize: 12, marginTop: 2 }}>acertos</Text>
                </View>

                <View style={{ width: 1, height: 38, backgroundColor: theme.border }} />

                <View style={{ alignItems: 'center' }}>
                  <Text style={{ color: theme.text, fontSize: 26, fontWeight: '700' }}>
                    {Math.round((totalGeral.acertos / totalGeral.total) * 100)}%
                  </Text>
                  <Text style={{ color: theme.inputLabel, fontSize: 12, marginTop: 2 }}>aproveitamento</Text>
                </View>

                <View style={{ width: 1, height: 38, backgroundColor: theme.border }} />

                <View style={{ alignItems: 'center' }}>
                  <Text style={{ color: theme.text, fontSize: 26, fontWeight: '700' }}>
                    {totalGeral.provas}
                  </Text>
                  <Text style={{ color: theme.inputLabel, fontSize: 12, marginTop: 2 }}>
                    {totalGeral.provas === 1 ? 'simulado' : 'simulados'}
                  </Text>
                </View>
              </View>

              {/* Quebra por matéria */}
              {Object.entries(porMateria)
                .sort((a, b) => b[1].total - a[1].total)
                .map(([materia, s]) => (
                  <View
                    key={materia}
                    style={{
                      backgroundColor: theme.card, borderColor: theme.border, borderWidth: 1,
                      borderRadius: 12, padding: 14, marginTop: 10,
                    }}
                  >
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Text
                        style={{ color: theme.text, fontWeight: '600', flex: 1, marginRight: 8 }}
                        numberOfLines={1}
                      >
                        {materia}
                      </Text>
                      <Text style={{ color: theme.text, fontWeight: '700' }}>
                        {s.acertos}
                        <Text style={{ color: theme.inputLabel, fontWeight: '500' }}>{` / ${s.total}`}</Text>
                        <Text style={{ color: theme.inputLabel, fontWeight: '500', fontSize: 12 }}>
                          {`  (${s.percentualAcerto}%)`}
                        </Text>
                      </Text>
                    </View>

                    <View style={{
                      height: 6, borderRadius: 3, marginTop: 8, overflow: 'hidden',
                      backgroundColor: isDarkMode ? '#2a2a3d' : '#E8E8EC',
                    }}>
                      <View style={{
                        width: `${s.percentualAcerto}%`, height: '100%',
                        borderRadius: 3, backgroundColor: getMateriaCor(materia),
                      }} />
                    </View>
                  </View>
                ))}
            </>
          )}
        </View>

        {/* FORMULÁRIO */}
        <View style={styles.formSection}>
          <Text style={[styles.sectionTitle, { color: isDarkMode ? '#9775E4' : '#7D53DD' }]}>Meus dados</Text>

          <View style={[styles.inputContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <View style={styles.textWrapper}>
              <Text style={[styles.label, { color: theme.inputLabel }]}>Nome completo</Text>
              <TextInput style={[styles.input, { color: theme.text }]} value={nome} onChangeText={setNome} placeholder="Digite seu nome" placeholderTextColor="#999" />
            </View>
            <Feather name="user" size={22} color={theme.icon} />
          </View>

          <View style={[styles.inputContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <View style={styles.textWrapper}>
              <TextInput style={[styles.inputSimple, { color: theme.text }]} value={dataNasc} onChangeText={setDataNasc} placeholder="Data de nascimento" placeholderTextColor="#999" />
            </View>
            <MaterialIcons name="calendar-today" size={22} color={theme.icon} />
          </View>

          <View style={[styles.inputContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <View style={styles.textWrapper}>
              <TextInput style={[styles.inputSimple, { color: theme.text }]} value={celular} onChangeText={setCelular} placeholder="Celular (opcional)" placeholderTextColor="#999" keyboardType="phone-pad" />
            </View>
            <Feather name="smartphone" size={22} color={theme.icon} />
          </View>

          <View style={[styles.inputContainer, styles.inputDisabled, { backgroundColor: isDarkMode ? '#1a1a25' : '#EAEAEA' }]}>
            <View style={styles.textWrapper}>
              <Text style={[styles.label, { color: '#666' }]}>Email</Text>
              <Text style={[styles.textDisabled, { color: isDarkMode ? '#8C8C8C' : '#707070' }]}>
                {email || 'Não informado'}
              </Text>
            </View>
            <MaterialIcons name="mail-outline" size={22} color="#444" />
          </View>
        </View>

        <TouchableOpacity accessibilityRole="button"
          style={[styles.saveButton, loading && { opacity: 0.7 }]}
          onPress={handleSaveData}
          disabled={loading}
        >
          {loading ? <ActivityIndicator color="#FFF" /> : <Text style={styles.saveButtonText}>Salvar dados</Text>}
        </TouchableOpacity>
      </ScrollView>

      <NivelisModal {...modal} />
    </KeyboardAvoidingView>
  );
}