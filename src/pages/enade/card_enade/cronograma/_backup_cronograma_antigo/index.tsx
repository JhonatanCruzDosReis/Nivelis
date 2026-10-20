// ╔═══════════════════════════════════════════════════════════════════════╗
// ║  PARE. ESTE ARQUIVO NÃO É USADO PELO APLICATIVO.                      ║
// ║                                                                       ║
// ║  A tela de cronograma que roda é:                                     ║
// ║      src/pages/enade/card_enade/cronograma/index.tsx                  ║
// ║  (importada em src/routes/index.tsx, linha 22)                        ║
// ║                                                                       ║
// ║  Isto aqui é uma CÓPIA DE SEGURANÇA, parada em 06/10/2026, e ainda    ║
// ║  tem dois defeitos que a tela de verdade já não tem:                  ║
// ║                                                                       ║
// ║   • o índice de fim soma meia hora a mais — "09:00 - 11:00" é         ║
// ║     pintado até 11:30, e "07:00 - 07:00" vira evento de duração zero  ║
// ║   • "excluir" apaga na hora, sem perguntar e sem desfazer             ║
// ║                                                                       ║
// ║  Se você chegou aqui por uma busca e ia corrigir alguma coisa:        ║
// ║  corrija em cronograma/index.tsx. Mexer aqui não muda nada no app.    ║
// ║                                                                       ║
// ║  Ver LEIA.txt nesta pasta.                                            ║
// ╚═══════════════════════════════════════════════════════════════════════╝

import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, Image, TouchableOpacity, Dimensions, ScrollView, TextInput
} from 'react-native';
import { Ionicons, FontAwesome5, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTheme } from '../../../TemasAcoes/Temas';
import { corDoTextoSobre, sombraDoTextoSobre } from '../../../../../services/contraste';

const { width } = Dimensions.get('window');

const CHAVE_EVENTOS = '@meu_cronograma_eventos';
const DIAS_COLUNAS: string[] = ['Horário', 'DOM', 'SEG', 'TER', 'QUA', 'QUI', 'SEX', 'SAB'];
const CORES_DISPONIVEIS: string[] = [
  '#FF5733', '#FFC300', '#DAF7A6', '#10B981', '#3B82F6',
  '#6A5AE0', '#A855F7', '#EF4444', '#EC4899', '#F43F5E',
  '#64748B', '#111827', '#FFFFFF', '#000000', '#F59E0B'
];

const gerarHorarios = () => {
  const listaHorarios: string[] = [];
  for (let i = 0; i < 48; i++) {
    const totalMinutos = i * 30;
    const horas = Math.floor((totalMinutos / 60) % 24);
    const minutos = totalMinutos % 60;
    listaHorarios.push(`${String(horas).padStart(2, '0')}:${String(minutos).padStart(2, '0')}`);
  }
  return listaHorarios;
};

const HORARIOS_LINHAS = gerarHorarios();

interface Evento {
  id: string;
  nome: string;
  dia: string;
  inicioIdx: number;
  fimIdx: number;
  cor: string;
  horaStr: string;
}

// Extrai "HH" e "MM" da parte de uma horaStr ("HH:MM - HH:MM")
const parseHoraStr = (horaStr: string): { hIni: string; mIni: string; hFim: string; mFim: string } => {
  try {
    const partes = horaStr.split(' - ');
    const [hIni, mIni] = partes[0].split(':');
    const [hFim, mFim] = partes[1].split(':');
    return { hIni, mIni, hFim, mFim };
  } catch {
    return { hIni: '', mIni: '', hFim: '', mFim: '' };
  }
};

export default function Cronograma() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const theme = {
    bg:           isDarkMode ? "#050505"  : "#F5F5F7",
    headerBg:     isDarkMode ? "#050505"  : "#F5F5F7",
    card:         isDarkMode ? "#111218"  : "#FFFFFF",
    gridBg:       isDarkMode ? "#0F1015"  : "#FFFFFF",
    border:       isDarkMode ? "#1F222F"  : "#E5E7EB",
    gridHeaderBg: isDarkMode ? "#151722"  : "#F9FAFB",
    textPrimary:  isDarkMode ? "#FFFFFF"  : "#1F2937",
    textSecondary:isDarkMode ? "#797D9A"  : "#6B7280",
    iconButtonBg: isDarkMode ? "#16161A"  : "#EAEAEA",
    inputBg:      isDarkMode ? "#1A1C24"  : "#F3F4F6",
    bottomNavBg:  isDarkMode ? "#0A0A0A"  : "#FFFFFF",
    navInactive:  isDarkMode ? "#525876"  : "#8E94A6",
  };

  const [nomeUsuario, setNomeUsuario]     = useState('Usuário');
  const [avatarUri, setAvatarUri]         = useState<string | null>(null);
  const [eventosSalvos, setEventosSalvos] = useState<Evento[]>([]);
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [dadosCarregados, setDadosCarregados] = useState(false);

  const [eventoSelecionado, setEventoSelecionado] = useState<Evento | null>(null);
  // Quando não-null, o formulário está em modo de edição desse evento
  const [editandoEvento, setEditandoEvento] = useState<Evento | null>(null);

  const [novoEventoNome, setNovoEventoNome] = useState('');
  const [novoEventoCor, setNovoEventoCor]   = useState('#10B981');
  const [novoEventoDia, setNovoEventoDia]   = useState('SEG');
  const [horaInicio, setHoraInicio]         = useState('');
  const [minInicio, setMinInicio]           = useState('');
  const [horaFim, setHoraFim]               = useState('');
  const [minFim, setMinFim]                 = useState('');

  const salvarEventosNoStorage = async (novosEventos: Evento[]) => {
    try {
      await AsyncStorage.setItem(CHAVE_EVENTOS, JSON.stringify(novosEventos));
    } catch (e) {
      console.error("Erro ao salvar eventos:", e);
    }
  };

  useEffect(() => {
    const carregarDados = async () => {
      try {
        const perfil = await AsyncStorage.getItem('@user_profile_data');
        if (perfil) {
          const data = JSON.parse(perfil);
          setNomeUsuario(data.nome || "Usuário");
          setAvatarUri(data.avatarUri || null);
        }
        const eventos = await AsyncStorage.getItem(CHAVE_EVENTOS);
        if (eventos) {
          setEventosSalvos(JSON.parse(eventos));
        }
      } catch (e) {
        console.log(e);
      } finally {
        setDadosCarregados(true);
      }
    };
    carregarDados();
  }, []);

  const handleHora = (text: string, setter: (val: string) => void) => {
    let val = text.replace(/\D/g, '');
    if (val.length === 2 && parseInt(val, 10) > 23) val = '23';
    setter(val);
  };

  const handleMinuto = (text: string, setter: (val: string) => void) => {
    let val = text.replace(/\D/g, '');
    if (val.length > 0 && parseInt(val[0], 10) > 5) val = '5' + val.slice(1);
    setter(val);
  };

  const obterIndiceHorario = (hStr: string, mStr: string, isFim: boolean = false) => {
    const h = parseInt(hStr || '0', 10);
    const m = parseInt(mStr || '0', 10);
    if (isFim) {
      if (m < 30) return (h * 2) + 1;
      return (h * 2) + 2;
    }
    return (h * 2) + (m < 30 ? 0 : 1);
  };

  // Limpa o formulário e abre para criação de novo evento
  const abrirFormNovo = () => {
    setEditandoEvento(null);
    setEventoSelecionado(null);
    setNovoEventoNome('');
    setNovoEventoCor('#10B981');
    setNovoEventoDia('SEG');
    setHoraInicio('');
    setMinInicio('');
    setHoraFim('');
    setMinFim('');
    setIsFormVisible(true);
  };

  // Pré-preenche o formulário com os dados do evento e abre em modo edição
  const abrirEdicao = (ev: Evento) => {
    const { hIni, mIni, hFim, mFim } = parseHoraStr(ev.horaStr);
    setEditandoEvento(ev);
    setNovoEventoNome(ev.nome);
    setNovoEventoCor(ev.cor);
    setNovoEventoDia(ev.dia);
    setHoraInicio(hIni);
    setMinInicio(mIni);
    setHoraFim(hFim);
    setMinFim(mFim);
    setEventoSelecionado(null);
    setIsFormVisible(true);
  };

  const fecharForm = () => {
    setIsFormVisible(false);
    setEditandoEvento(null);
    setNovoEventoNome('');
  };

  const salvarEventoNaPlanilha = () => {
    if (!horaInicio || !minInicio || !horaFim || !minFim) return;

    const inicioIdx = obterIndiceHorario(horaInicio, minInicio, false);
    const fimIdx    = obterIndiceHorario(horaFim, minFim, true);

    if (inicioIdx === -1 || fimIdx === -1 || inicioIdx >= fimIdx) return;

    // Preserva o ID ao editar; gera novo ao criar
    const novoId = editandoEvento ? editandoEvento.id : Math.random().toString(36).substring(2, 9);

    const novoObjetoEvento: Evento = {
      id: novoId,
      nome: novoEventoNome || 'Evento',
      dia: novoEventoDia,
      inicioIdx,
      fimIdx,
      cor: novoEventoCor,
      horaStr: `${horaInicio.padStart(2, '0')}:${minInicio.padStart(2, '0')} - ${horaFim.padStart(2, '0')}:${minFim.padStart(2, '0')}`
    };

    // Em modo edição: exclui o evento original da lista base antes de resolver conflitos
    const listaBase = editandoEvento
      ? eventosSalvos.filter(e => e.id !== editandoEvento.id)
      : eventosSalvos;

    const eventosFiltrados: Evento[] = [];

    for (const ev of listaBase) {
      if (ev.dia === novoEventoDia && inicioIdx < ev.fimIdx && fimIdx > ev.inicioIdx) {
        // Conflito: fatia o evento existente para ceder espaço
        if (ev.inicioIdx < inicioIdx) {
          eventosFiltrados.push({
            ...ev,
            id: Math.random().toString(36).substring(2, 9),
            fimIdx: inicioIdx,
            horaStr: `${HORARIOS_LINHAS[ev.inicioIdx]} - ${HORARIOS_LINHAS[inicioIdx]}`
          });
        }
        if (ev.fimIdx > fimIdx) {
          eventosFiltrados.push({
            ...ev,
            id: Math.random().toString(36).substring(2, 9),
            inicioIdx: fimIdx,
            horaStr: `${HORARIOS_LINHAS[fimIdx]} - ${HORARIOS_LINHAS[ev.fimIdx] || '23:59'}`
          });
        }
      } else {
        eventosFiltrados.push(ev);
      }
    }

    const novaLista = [...eventosFiltrados, novoObjetoEvento];
    setEventosSalvos(novaLista);
    salvarEventosNoStorage(novaLista);

    fecharForm();
  };

  const removerEvento = () => {
    if (!eventoSelecionado) return;
    const novaLista = eventosSalvos.filter(e => e.id !== eventoSelecionado.id);
    setEventosSalvos(novaLista);
    salvarEventosNoStorage(novaLista);
    setEventoSelecionado(null);
  };

  const modoEdicao = editandoEvento !== null;

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>

      {/* HEADER */}
      <View style={[styles.header, { backgroundColor: theme.headerBg }]}>
        <TouchableOpacity
          onPress={() => navigation.navigate('EnemEnade')}
          style={[styles.iconButton, { backgroundColor: theme.iconButtonBg }]}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color={theme.textPrimary} />
        </TouchableOpacity>
        <TouchableOpacity style={styles.rowCenter} onPress={() => navigation.navigate('MeusDados')}>
          <View style={styles.userInfo}>
            <Text style={[styles.greetingText, { color: theme.textSecondary }]}>BONS ESTUDOS,</Text>
            <Text style={[styles.userName, { color: theme.textPrimary }]}>{nomeUsuario}</Text>
          </View>
          {avatarUri ? (
            <Image source={{ uri: avatarUri }} style={styles.profilePic} />
          ) : (
            <View style={[styles.profilePic, styles.profilePlaceholder, { backgroundColor: theme.iconButtonBg }]}>
              <FontAwesome5 name="user-alt" size={18} color="#6B21A8" />
            </View>
          )}
        </TouchableOpacity>
      </View>

      {/* FORMULÁRIO — ADICIONAR ou EDITAR */}
      {isFormVisible && (
        <View style={styles.formOverlay}>
          <View style={[styles.formContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <View style={styles.formHeader}>
              <Text style={styles.formTitle}>
                {modoEdicao ? 'EDITAR EVENTO' : 'ADICIONAR EVENTO'}
              </Text>
              <TouchableOpacity onPress={fecharForm}
                accessibilityRole="button"
                accessibilityLabel="Fechar"
              >
                <Ionicons name="close" size={24} color={theme.textSecondary} />
              </TouchableOpacity>
            </View>

            <TextInput
              style={[styles.input, { backgroundColor: theme.inputBg, color: theme.textPrimary }]}
              placeholder="Nome do evento"
              placeholderTextColor={theme.textSecondary}
              value={novoEventoNome}
              onChangeText={setNovoEventoNome}
            />

            <Text style={[styles.label, { color: theme.textSecondary }]}>Dia</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.daysScroll}>
              {DIAS_COLUNAS.slice(1).map(dia => (
                <TouchableOpacity
                  key={dia}
                  style={[
                    styles.daySelector,
                    { backgroundColor: theme.inputBg },
                    novoEventoDia === dia && styles.daySelectorActive
                  ]}
                  onPress={() => setNovoEventoDia(dia)}
                >
                  <Text style={[
                    styles.dayText,
                    { color: theme.textSecondary },
                    novoEventoDia === dia && styles.dayTextActive
                  ]}>{dia}</Text>
                </TouchableOpacity>
              ))}
            </ScrollView>

            <View style={styles.rowForm}>
              <View style={styles.flexItemHalf}>
                <Text style={[styles.label, { color: theme.textSecondary }]}>Início</Text>
                <View style={styles.timeInputRow}>
                  <TextInput
                    style={[styles.timeInputBox, { backgroundColor: theme.inputBg, color: theme.textPrimary }]}
                    placeholder="HH" placeholderTextColor={theme.textSecondary}
                    value={horaInicio} maxLength={2} keyboardType="numeric"
                    onChangeText={(t) => handleHora(t, setHoraInicio)}
                  />
                  <Text style={[styles.colonText, { color: theme.textPrimary }]}>:</Text>
                  <TextInput
                    style={[styles.timeInputBox, { backgroundColor: theme.inputBg, color: theme.textPrimary }]}
                    placeholder="MM" placeholderTextColor={theme.textSecondary}
                    value={minInicio} maxLength={2} keyboardType="numeric"
                    onChangeText={(t) => handleMinuto(t, setMinInicio)}
                  />
                </View>
              </View>
              <View style={styles.flexItemHalf}>
                <Text style={[styles.label, { color: theme.textSecondary }]}>Fim</Text>
                <View style={styles.timeInputRow}>
                  <TextInput
                    style={[styles.timeInputBox, { backgroundColor: theme.inputBg, color: theme.textPrimary }]}
                    placeholder="HH" placeholderTextColor={theme.textSecondary}
                    value={horaFim} maxLength={2} keyboardType="numeric"
                    onChangeText={(t) => handleHora(t, setHoraFim)}
                  />
                  <Text style={[styles.colonText, { color: theme.textPrimary }]}>:</Text>
                  <TextInput
                    style={[styles.timeInputBox, { backgroundColor: theme.inputBg, color: theme.textPrimary }]}
                    placeholder="MM" placeholderTextColor={theme.textSecondary}
                    value={minFim} maxLength={2} keyboardType="numeric"
                    onChangeText={(t) => handleMinuto(t, setMinFim)}
                  />
                </View>
              </View>
            </View>

            <View style={styles.colorPickerContainer}>
              {CORES_DISPONIVEIS.map(cor => (
                <TouchableOpacity
                  key={cor}
                  style={[
                    styles.colorCircle,
                    { backgroundColor: cor },
                    novoEventoCor === cor && styles.colorCircleActive
                  ]}
                  onPress={() => setNovoEventoCor(cor)}
                />
              ))}
            </View>

            <TouchableOpacity
              style={[styles.saveButton, modoEdicao && styles.saveButtonEdit]}
              onPress={salvarEventoNaPlanilha}
            >
              <Text style={styles.saveButtonText}>
                {modoEdicao ? 'ATUALIZAR' : 'SALVAR'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      {/* PLANILHA */}
      <View style={[styles.gridContainer, { backgroundColor: theme.gridBg, borderColor: theme.border }]}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false}>
          <View>
            {/* Header fixo com dias */}
            <View style={styles.tableRow}>
              {DIAS_COLUNAS.map((dia, index) => (
                <View
                  key={dia}
                  style={[
                    styles.cell, styles.headerCell,
                    { backgroundColor: theme.gridHeaderBg, borderColor: theme.border },
                    index === 0 ? styles.timeColumnConfig : styles.dayColumnConfig
                  ]}
                >
                  <Text style={[styles.headerText, index === 0 && { color: theme.textSecondary }]}>{dia}</Text>
                </View>
              ))}
            </View>

            <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom: 200 }}>
              {HORARIOS_LINHAS.map((horario, rowIndex) => (
                <View key={rowIndex} style={styles.tableRow}>
                  <View style={[styles.cell, styles.timeCell, { backgroundColor: theme.gridHeaderBg, borderColor: theme.border }, styles.timeColumnConfig]}>
                    <Text style={[styles.timeText, { color: theme.textSecondary }]}>{horario}</Text>
                  </View>
                  {Array.from({ length: 7 }).map((_, dIdx) => {
                    const diaNome = DIAS_COLUNAS[dIdx + 1];
                    const ev = eventosSalvos.find(e => e.dia === diaNome && rowIndex >= e.inicioIdx && rowIndex < e.fimIdx);
                    const isSelected = ev && eventoSelecionado && ev.id === eventoSelecionado.id;
                    return (
                      <TouchableOpacity
                        key={dIdx}
                        activeOpacity={0.7}
                        onPress={() => {
                          if (ev) setEventoSelecionado(isSelected ? null : ev);
                        }}
                        style={[
                          styles.cell,
                          styles.contentCell,
                          styles.dayColumnConfig,
                          { backgroundColor: theme.gridBg, borderColor: theme.border },
                          ev && { backgroundColor: ev.cor },
                          isSelected && styles.cellSelected,
                        ]}
                      >
                        {ev && rowIndex === ev.inicioIdx && (
                          <Text numberOfLines={2}
                                style={[styles.eventSlotText,
                                        { color: corDoTextoSobre(ev.cor),
                                          textShadowColor: sombraDoTextoSobre(ev.cor) }]}>
                            {ev.nome}
                          </Text>
                        )}
                        {ev && rowIndex === ev.inicioIdx + 1 && (
                          <Text numberOfLines={1}
                                style={[styles.eventSlotText,
                                        { color: corDoTextoSobre(ev.cor),
                                          textShadowColor: sombraDoTextoSobre(ev.cor) }]}>
                            {ev.horaStr}
                          </Text>
                        )}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ))}
            </ScrollView>
          </View>
        </ScrollView>
      </View>

      {/* BARRA INFERIOR + EVENTO SELECIONADO */}
      <View style={[styles.floatingBottomContainer, { backgroundColor: theme.bg }]}>
        {!isFormVisible && (
          <View style={styles.eventsContainer}>
            <Text style={[styles.sectionTitle, { color: isDarkMode ? '#A78BFA' : '#5B4BC4' }]}>
              {eventoSelecionado ? 'EVENTO SELECIONADO' : 'NENHUM EVENTO SELECIONADO'}
            </Text>

            {eventoSelecionado ? (
              <View style={[styles.eventCard, { backgroundColor: theme.card, borderLeftColor: eventoSelecionado.cor }]}>
                <View style={[styles.iconBox, { backgroundColor: eventoSelecionado.cor }]}>
                  <Ionicons name="reader-outline" size={18} color="#FFF" />
                </View>
                <View style={styles.eventInfo}>
                  <View style={styles.eventHeaderRow}>
                    <Text style={[styles.eventTitle, { color: theme.textPrimary }]} numberOfLines={1}>
                      {eventoSelecionado.nome}
                    </Text>
                    <View style={styles.actionButtons}>
                      {/* Editar */}
                      <TouchableOpacity
                        onPress={() => abrirEdicao(eventoSelecionado)}
                        style={styles.editButton}
                      >
                        <Ionicons name="pencil-outline" size={12} color="#FFF" />
                        <Text style={styles.actionButtonText}>editar</Text>
                      </TouchableOpacity>
                      {/* Excluir */}
                      <TouchableOpacity
                        onPress={removerEvento}
                        style={styles.deleteButton}
                      >
                        <Ionicons name="trash-outline" size={12} color="#FFF" />
                        <Text style={styles.actionButtonText}>excluir</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                  <Text style={[styles.eventTime, { color: theme.textSecondary }]}>
                    {eventoSelecionado.dia} · {eventoSelecionado.horaStr}
                  </Text>
                </View>
              </View>
            ) : (
              <View style={[styles.emptyEventBox, { backgroundColor: theme.card }]}>
                <Text style={[styles.emptyEventText, { color: theme.textSecondary }]}>
                  Toque em um evento na tabela para editar ou remover.
                </Text>
              </View>
            )}
          </View>
        )}

        <View style={[styles.bottomNav, { backgroundColor: theme.bottomNavBg, borderTopColor: theme.border }]}>
  
  {/* CRONOGRAMA */}
  <TouchableOpacity style={styles.navItem}>
    <Ionicons name="calendar-outline" size={24} color="#A855F7" />
    <Text style={[styles.navText, { color: '#A855F7' }]}>Cronograma</Text>
  </TouchableOpacity>

  {/* LIVROS  */}
  <TouchableOpacity onPress={() => navigation.navigate('LivrosEnade')} style={styles.navItem}>
    <Ionicons name="book-outline" size={24} color={isDarkMode ? "#D1D5DB" : "#4B5563"} />
    <Text style={[styles.navText, { color: theme.navInactive }]}>Livros</Text>
  </TouchableOpacity>

  {/* MATÉRIAS */}
  <TouchableOpacity onPress={() => navigation.navigate('materia')} style={styles.navItem}>
    <Ionicons name="school-outline" size={24} color={isDarkMode ? "#D1D5DB" : "#4B5563"} />
    <Text style={[styles.navText, { color: theme.navInactive }]}>Matérias</Text>
  </TouchableOpacity>
  {/* SIMULADOS  */}
  <TouchableOpacity onPress={() => navigation.navigate('SimuladosDashboard')} style={styles.navItem}>
    <MaterialCommunityIcons name="clipboard-text-outline" size={24} color={isDarkMode ? "#D1D5DB" : "#4B5563"} />
    <Text style={[styles.navText, { color: theme.navInactive }]}>Simulados</Text>
  </TouchableOpacity>
  </View>
      </View>

      {/* FAB — sempre abre formulário limpo */}
      <TouchableOpacity
        style={styles.fabButton}
        activeOpacity={0.8}
        onPress={() => isFormVisible ? fecharForm() : abrirFormNovo()}
        accessibilityRole="button"
        accessibilityLabel={isFormVisible ? "Fechar o formulário" : "Novo evento no cronograma"}
      >
        <Ionicons name={isFormVisible ? "close" : "add"} size={28} color="#000" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  /*== HEADER ==*/
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 60, marginBottom: 15, paddingHorizontal: 15 },
  rowCenter: { flexDirection: 'row', alignItems: 'center' },
  userInfo: { marginRight: 10, alignItems: 'flex-end' },
  greetingText: { fontSize: 10, fontWeight: 'bold' },
  userName: { fontSize: 16, fontWeight: 'bold' },
  profilePic: { width: 40, height: 40, borderRadius: 20, borderWidth: 2, borderColor: '#6B21A8' },
  profilePlaceholder: { justifyContent: 'center', alignItems: 'center' },
  iconButton: { padding: 10, borderRadius: 50 },

  /*== PLANILHA ==*/
  gridContainer: { flex: 1, marginHorizontal: 10, borderRadius: 12, borderWidth: 1, overflow: 'hidden' },
  tableRow: { flexDirection: 'row' },
  cell: { justifyContent: 'center', alignItems: 'center', borderBottomWidth: 1 },
  timeColumnConfig: { width: 50 },
  dayColumnConfig: { width: 60 },
  headerCell: { height: 40 },
  headerText: { color: '#6A5AE0', fontWeight: 'bold', fontSize: 11 },
  timeCell: { height: 45 },
  timeText: { fontSize: 11, fontWeight: '500' },
  contentCell: { height: 45 },
  cellSelected: { borderWidth: 2, borderColor: '#FBBF24' },
  eventSlotText: { fontSize: 11, fontWeight: 'bold', textAlign: 'center', paddingHorizontal: 2, textShadowColor: 'rgba(0,0,0,0.4)', textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 2 },

  /*== NAVBAR E EVENTO SELECIONADO ==*/
  floatingBottomContainer: { position: 'absolute', bottom: 0, width: '100%', borderTopLeftRadius: 15, borderTopRightRadius: 15, zIndex: 1000, elevation: 10 },
  fabButton: { position: 'absolute', right: 20, bottom: 200, backgroundColor: '#FBBF24', width: 46, height: 46, borderRadius: 23, justifyContent: 'center', alignItems: 'center', zIndex: 1001, elevation: 11 },
  eventsContainer: { paddingHorizontal: 15, paddingTop: 10, paddingBottom: 10 },
  sectionTitle: { fontSize: 10, fontWeight: 'bold', marginBottom: 5 },
  eventCard: { flexDirection: 'row', borderRadius: 12, padding: 10, alignItems: 'center', borderLeftWidth: 3 },
  iconBox: { width: 30, height: 30, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  eventInfo: { flex: 1 },
  eventHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  eventTitle: { fontSize: 12, fontWeight: 'bold', flex: 1 },
  actionButtons: { flexDirection: 'row', gap: 6 },
  editButton: { flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: '#6A5AE0', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 5 },
  deleteButton: { flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: '#EF4444', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 5 },
  actionButtonText: { color: '#FFF', fontSize: 10, fontWeight: 'bold' },
  eventTime: { fontSize: 10, marginTop: 1 },
  emptyEventBox: { padding: 10, borderRadius: 12, alignItems: 'center', justifyContent: 'center', height: 50 },
  emptyEventText: { fontSize: 10 },

  /*== FORMULÁRIO ==*/
  formOverlay: { position: 'absolute', top: 120, left: 10, right: 10, zIndex: 50 },
  formContainer: { padding: 15, borderRadius: 15, borderWidth: 1 },
  formHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  formTitle: { color: '#A855F7', fontSize: 12, fontWeight: 'bold' },
  input: { paddingHorizontal: 10, paddingVertical: 8, borderRadius: 8, fontSize: 12, marginBottom: 10 },
  label: { fontSize: 11, fontWeight: 'bold', textTransform: 'uppercase',
           letterSpacing: 0.3 },
  rowForm: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  flexItemHalf: { flex: 0.48 },
  timeInputRow: { flexDirection: 'row', alignItems: 'center' },
  timeInputBox: { flex: 1, padding: 8, borderRadius: 8, textAlign: 'center' },
  colonText: { marginHorizontal: 4 },
  daysScroll: { marginBottom: 10 },
  daySelector: { paddingHorizontal: 12, paddingVertical: 8, borderRadius: 8, marginRight: 8 },
  daySelectorActive: { backgroundColor: '#6A5AE0' },
  dayText: { fontSize: 11, fontWeight: 'bold' },
  dayTextActive: { color: '#FFF' },
  colorPickerContainer: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: 10, gap: 5 },
  colorCircle: { width: 28, height: 28, borderRadius: 14, borderWidth: 1,
                 borderColor: 'rgba(128,128,128,0.45)' },
  colorCircleActive: { opacity: 1, borderWidth: 2, borderColor: '#000' },
  saveButton: { backgroundColor: '#6A5AE0', padding: 10, borderRadius: 8, alignItems: 'center' },
  saveButtonEdit: { backgroundColor: '#F59E0B' },
  saveButtonText: { color: '#FFF', fontSize: 12, fontWeight: 'bold' },

  /*== NAVEGAÇÃO ==*/
  bottomNav: { flexDirection: 'row', justifyContent: 'space-around', paddingVertical: 20, paddingBottom: 25, borderTopWidth: 1 },
  navItem: { alignItems: 'center',flex: 1 },
  navText: { fontSize: 9, marginTop: 5 },
});
