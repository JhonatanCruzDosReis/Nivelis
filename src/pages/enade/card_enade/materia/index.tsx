import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, Image, TouchableOpacity, TextInput,
  ScrollView, StatusBar, LayoutAnimation, Platform, UIManager
} from 'react-native';
import { Ionicons, FontAwesome5 } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { useTheme } from '../../../TemasAcoes/Temas';
import { MATERIAS, Aula, Materia } from '../../../../data/materiasData';

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true);
}

export default function MateriasScreen() {
  const navigation  = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [nomeUsuario,       setNomeUsuario]       = useState('Usuário');
  const [avatarUri,         setAvatarUri]         = useState<string | null>(null);
  const [busca,             setBusca]             = useState('');
  const [materiaAberta,     setMateriaAberta]     = useState<string | null>('mat');
  const [subtopicosAbertos, setSubtopicosAbertos] = useState<string[]>(['mat_alg']);

  const theme = {
    bg:           isDarkMode ? '#000000' : '#F5F5F7',
    card:         isDarkMode ? '#0A0A0A' : '#FFFFFF',
    cardSec:      isDarkMode ? '#121212' : '#F8F8F8',
    text:         isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:          isDarkMode ? '#888888' : '#666666',
    border:       isDarkMode ? '#222222' : '#E5E5E5',
    iconBg:       isDarkMode ? "#16161A"  : "#EAEAEA",
    accent:       '#7D53DD',
  };

  useEffect(() => {
    AsyncStorage.getItem('@user_profile_data').then(raw => {
      if (raw) {
        const data = JSON.parse(raw);
        setNomeUsuario(data.nome || 'Usuário');
        setAvatarUri(data.avatarUri || null);
      }
    }).catch(console.log);
  }, []);

  const toggleMateria = (id: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setMateriaAberta(prev => prev === id ? null : id);
  };

  const toggleSubtopico = (id: string) => {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut);
    setSubtopicosAbertos(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  const irParaAula = (aula: Aula, materia: Materia) => {
    navigation.navigate('AulaPlayer', {
      titulo:      aula.titulo,
      duracao:     aula.duracao,
      materiaId:   materia.id,
      materiaNome: materia.nome,
      videoId:   aula.videoId,
          videoTipo: aula.videoTipo ?? 'youtube',
    });
  };

  const materiasFiltradas = MATERIAS.filter(m =>
    m.nome.toLowerCase().includes(busca.toLowerCase()) ||
    m.subtopicos.some(s => s.nome.toLowerCase().includes(busca.toLowerCase())) ||
    m.subtopicos.some(s => s.aulas.some(a => a.titulo.toLowerCase().includes(busca.toLowerCase())))
  );

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* HEADER */}
      <View style={styles.header}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
          onPress={() => navigation.goBack()}
          style={[styles.iconBtn, { backgroundColor: theme.iconBg }]}
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
            <Text style={[styles.greeting, { color: theme.sub }]}>BONS ESTUDOS,</Text>
            <Text style={[styles.userName, { color: theme.text }]}>{nomeUsuario}</Text>
          </View>
          {avatarUri ? (
            <Image source={{ uri: avatarUri }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarPlaceholder, { backgroundColor: theme.iconBg }]}>
              <FontAwesome5 name="user-alt" size={18} color={theme.accent} />
            </View>
          )}
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

        {/* BUSCA */}
        <View style={[styles.searchBox, { backgroundColor: theme.card, borderColor: theme.border }]}>
          <Ionicons name="search" size={20} color={theme.sub} />
          <TextInput
            placeholder="Buscar matérias ou aulas..."
            placeholderTextColor={theme.sub}
            style={[styles.searchInput, { color: theme.text }]}
            value={busca}
            onChangeText={setBusca}
          />
          {busca.length > 0 && (
            <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => setBusca('')}
              accessibilityRole="button"
              accessibilityLabel="Fechar"
            >
              <Ionicons name="close-circle" size={18} color={theme.sub} />
            </TouchableOpacity>
          )}
        </View>

        {/* LISTA DE MATÉRIAS (ACCORDION) */}
        <View style={styles.list}>
          {materiasFiltradas.map(materia => {
            const aberta = materiaAberta === materia.id;
            const totalAulas = materia.subtopicos.reduce((acc, s) => acc + s.aulas.length, 0);

            return (
              <View
                key={materia.id}
                style={[
                  styles.materiaCard,
                  { backgroundColor: theme.card, borderColor: theme.border },
                  aberta && { paddingBottom: 12 },
                ]}
              >
                {/* CABEÇALHO DA MATÉRIA */}
                <TouchableOpacity accessibilityRole="button"
                  style={styles.materiaHeader}
                  activeOpacity={0.7}
                  onPress={() => toggleMateria(materia.id)}
                >
                  <View style={styles.materiaLeft}>
                    <View style={[styles.materiaIconWrap, { backgroundColor: materia.cor + '18' }]}>
                      <FontAwesome5 name={materia.icone as any} size={18} color={materia.cor} />
                    </View>
                    <View>
                      <Text style={[styles.materiaNome, { color: theme.text }]}>{materia.nome}</Text>
                      <Text style={[styles.materiaCount, { color: theme.sub }]}>
                        {totalAulas} aula{totalAulas !== 1 ? 's' : ''} · {materia.subtopicos.length} módulo{materia.subtopicos.length !== 1 ? 's' : ''}
                      </Text>
                    </View>
                  </View>
                  <Ionicons
                    name={aberta ? 'chevron-up' : 'chevron-down'}
                    size={20}
                    color={theme.sub}
                  />
                </TouchableOpacity>

                {/* SUBTÓPICOS */}
                {aberta && materia.subtopicos.map(sub => {
                  const subAberto = subtopicosAbertos.includes(sub.id);

                  return (
                    <View
                      key={sub.id}
                      style={[styles.subCard, { backgroundColor: theme.cardSec, borderColor: theme.border }]}
                    >
                      {/* Cabeçalho do subtópico */}
                      <TouchableOpacity accessibilityRole="button"
                        style={styles.subHeader}
                        activeOpacity={0.7}
                        onPress={() => toggleSubtopico(sub.id)}
                      >
                        <View style={styles.materiaLeft}>
                          <Ionicons name="folder-outline" size={18} color={theme.sub} />
                          <Text style={[styles.subNome, { color: theme.text }]}>{sub.nome}</Text>
                        </View>
                        <View style={styles.subRight}>
                          <Text style={[styles.subCount, { color: theme.sub }]}>
                            {sub.aulas.length} aula{sub.aulas.length !== 1 ? 's' : ''}
                          </Text>
                          <Ionicons
                            name={subAberto ? 'chevron-up' : 'chevron-down'}
                            size={16}
                            color={theme.sub}
                          />
                        </View>
                      </TouchableOpacity>

                      {/* LISTA DE AULAS */}
                      {subAberto && sub.aulas.map((aula, idx) => (
                        <TouchableOpacity accessibilityRole="button"
                          key={aula.id}
                          style={[
                            styles.aulaRow,
                            { borderTopColor: theme.border },
                            idx === 0 && { marginTop: 4 },
                          ]}
                          activeOpacity={0.7}
                          onPress={() => irParaAula(aula, materia)}
                        >
                          <View style={styles.aulaLeft}>
                            {/* Indicador: vídeo disponível vs. em produção */}
                            <View style={[
                              styles.aulaPlayCircle,
                              { backgroundColor: aula.videoId ? materia.cor + '20' : '#F59E0B20' },
                            ]}>
                              <Ionicons
                                name={aula.videoId ? 'play-circle-outline' : 'time-outline'}
                                size={20}
                                color={aula.videoId ? materia.cor
                                                    : (isDarkMode ? '#F59E0B' : '#92400E')}
                              />
                            </View>
                            <View style={{ flex: 1 }}>
                              <Text style={[styles.aulaTitulo, { color: theme.text }]} numberOfLines={1}>
                                {aula.titulo}
                              </Text>
                              {/* No claro, o âmbar cheio sobre o fundo claro dava
                                  2.02:1 — ilegível. Escurece só no tema claro. */}
                              {!aula.videoId && (
                                <Text style={[styles.aulaProd,
                                              { color: isDarkMode ? '#F59E0B' : '#92400E' }]}>
                                  Em produção
                                </Text>
                              )}
                            </View>
                          </View>
                          <Text style={[styles.aulaDuracao, { color: theme.sub }]}>{aula.duracao}</Text>
                        </TouchableOpacity>
                      ))}
                    </View>
                  );
                })}
              </View>
            );
          })}

          {materiasFiltradas.length === 0 && (
            <View style={styles.emptyState}>
              <Ionicons name="search-outline" size={48} color={theme.sub} />
              <Text style={[styles.emptyText, { color: theme.sub }]}>
                Nenhuma matéria encontrada para "{busca}"
              </Text>
            </View>
          )}
        </View>

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { paddingBottom: 50 },

  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 60,
    marginBottom: 20,
    paddingHorizontal: 20,
  },
  rowCenter: { flexDirection: 'row', alignItems: 'center' },
  userInfo:  { marginRight: 10, alignItems: 'flex-end' },
  greeting:  { fontSize: 10, fontWeight: 'bold' },
  userName:  { fontSize: 16, fontWeight: 'bold' },
  avatar:    { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: '#7D53DD' },
  avatarPlaceholder: { justifyContent: 'center', alignItems: 'center' },
  iconBtn:   { padding: 10, borderRadius: 50 },

  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 20,
    paddingHorizontal: 15,
    height: 50,
    borderRadius: 14,
    borderWidth: 1,
    marginBottom: 24,
    gap: 10,
  },
  searchInput: { flex: 1, fontSize: 15 },

  list: { paddingHorizontal: 20, gap: 12 },

  // Matéria card
  materiaCard: {
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },
  materiaHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
  },
  materiaLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  materiaIconWrap: {
    width: 44, height: 44, borderRadius: 12,
    justifyContent: 'center', alignItems: 'center',
  },
  materiaNome:  { fontSize: 17, fontWeight: 'bold' },
  materiaCount: { fontSize: 11, marginTop: 2 },

  // Subtópico card
  subCard: {
    marginHorizontal: 12,
    marginBottom: 10,
    borderRadius: 10,
    borderWidth: 1,
    overflow: 'hidden',
  },
  subHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 14,
  },
  subNome:  { fontSize: 12, fontWeight: 'bold', letterSpacing: 0.5, marginLeft: 10 },
  subRight: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  subCount: { fontSize: 11 },

  // Aula row
  aulaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderTopWidth: 0.5,
  },
  aulaLeft: { flexDirection: 'row', alignItems: 'center', flex: 1, gap: 10, marginRight: 8 },
  aulaPlayCircle: {
    width: 36, height: 36, borderRadius: 18,
    justifyContent: 'center', alignItems: 'center',
    flexShrink: 0,
  },
  aulaTitulo:  { fontSize: 13, fontWeight: '500' },
  aulaProd:    { fontSize: 10, color: '#F59E0B', marginTop: 1 },
  aulaDuracao: { fontSize: 11 },

  // Empty state
  emptyState: { alignItems: 'center', paddingTop: 60, gap: 12 },
  emptyText:  { fontSize: 14, textAlign: 'center' },
});
