import React, { useState, useEffect } from 'react';
import {
  StyleSheet, Text, View, Image, TouchableOpacity, Dimensions, ScrollView, TextInput, Modal
} from 'react-native';
import { Ionicons, FontAwesome5, MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTheme } from '../../../TemasAcoes/Temas';
import { corDoTextoSobre, sombraDoTextoSobre } from '../../../../services/contraste';

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

/**
 * Converte "HH" e "MM" no índice da linha da grade.
 *
 * Cada linha é uma faixa de 30 minutos: a linha 18 é "09:00" e cobre de
 * 09:00 até 09:30. O início arredonda PARA BAIXO (quem começa 09:15
 * aparece já na faixa das 09:00) e o fim arredonda PARA CIMA, porque o
 * fim é exclusivo — a grade pinta enquanto `rowIndex < fimIdx`.
 *
 * ── o bug que isto conserta ──
 * A conta antiga do fim era `m < 30 ? h*2+1 : h*2+2`, que somava uma
 * faixa inteira em cima de qualquer horário redondo. Um evento marcado
 * "09:00 - 11:00" recebia fimIdx 23 e era pintado até 11:30: meia hora a
 * mais do que dizia o próprio horaStr, escrito logo abaixo do nome do
 * evento. Em 7 dos 9 horários que testei o bloco desenhado discordava do
 * rótulo, e os 2 que acertavam eram justamente os de minuto quebrado —
 * ou seja, o erro pegava exatamente quem digita hora cheia.
 *
 * Pior: "07:00 - 07:00" dava inicioIdx 14 e fimIdx 15, passava pela
 * checagem de duração e virava um evento de comprimento zero ocupando
 * meia hora da semana. Com `ceil` os dois índices dão 14, a checagem
 * `inicioIdx >= fimIdx` finalmente reprova, e o usuário recebe um aviso.
 */
const obterIndiceHorario = (hStr: string, mStr: string, isFim: boolean = false): number => {
  const h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10);
  if (Number.isNaN(h) || Number.isNaN(m)) return -1;
  if (h < 0 || h > 23 || m < 0 || m > 59) return -1;
  const minutos = h * 60 + m;
  return isFim ? Math.ceil(minutos / 30) : Math.floor(minutos / 30);
};

/**
 * Recalcula os índices dos eventos que já estão salvos no aparelho.
 *
 * Quem usou o cronograma antes desta correção tem eventos gravados com o
 * fimIdx inflado. Só trocar a fórmula arruma os eventos novos e deixa os
 * antigos errados para sempre, então a lista passa por aqui ao carregar.
 *
 * O horaStr é a fonte da verdade: foi o que o usuário digitou. Os índices
 * são derivados dele. Eventos cujo horaStr não dá para ler ficam como
 * estão — melhor um evento antigo torto do que um evento apagado.
 *
 * A conta é idempotente: reprocessar uma lista já corrigida devolve os
 * mesmos índices, então isto pode rodar em todo carregamento sem acumular
 * desvio.
 */
const corrigirIndices = (lista: Evento[]): { lista: Evento[]; mudou: boolean } => {
  let mudou = false;
  const corrigida = lista.map(ev => {
    const { hIni, mIni, hFim, mFim } = parseHoraStr(ev.horaStr ?? '');
    const ini = obterIndiceHorario(hIni, mIni, false);
    const fim = obterIndiceHorario(hFim, mFim, true);
    if (ini < 0 || fim < 0 || ini >= fim) return ev;      // ilegível: não mexe
    if (ini === ev.inicioIdx && fim === ev.fimIdx) return ev;
    mudou = true;
    return { ...ev, inicioIdx: ini, fimIdx: fim };
  });
  return { lista: corrigida, mudou };
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
    textSecondary:isDarkMode ? "#7C809C"  : "#666C79",   // 4.43/4.44 → 4.6+
    iconButtonBg: isDarkMode ? "#16161A"  : "#EAEAEA",
    inputBg:      isDarkMode ? "#1A1C24"  : "#F3F4F6",
    bottomNavBg:  isDarkMode ? "#0A0A0A"  : "#FFFFFF",
    navInactive:  isDarkMode ? "#757991"  : "#727685",   // 2.84/3.03 → 4.6/4.52

    // Estes dois estavam fixos no StyleSheet, iguais nos dois temas — e um
    // roxo só não serve para fundo claro e escuro ao mesmo tempo. O #6A5AE0
    // dos cabeçalhos de dia dava 3.53:1 sobre a faixa escura; o #A855F7 do
    // item ativo dava 3.96:1 sobre o branco.
    roxoCabecalho: isDarkMode ? "#7F71E4" : "#6A5AE0",   // 3.53 → 4.57
    roxoAtivo:     isDarkMode ? "#A855F7" : "#9B4EE3",   // 3.96 → 4.57
  };

  const [nomeUsuario, setNomeUsuario]     = useState('Usuário');
  const [avatarUri, setAvatarUri]         = useState<string | null>(null);
  const [eventosSalvos, setEventosSalvos] = useState<Evento[]>([]);
  const [isFormVisible, setIsFormVisible] = useState(false);
  const [dadosCarregados, setDadosCarregados] = useState(false);

  const [eventoSelecionado, setEventoSelecionado] = useState<Evento | null>(null);
  // Quando não-null, o formulário está em modo de edição desse evento
  const [editandoEvento, setEditandoEvento] = useState<Evento | null>(null);
  // Quando não-null, está esperando o usuário confirmar a exclusão desse evento
  const [confirmandoExclusao, setConfirmandoExclusao] = useState<Evento | null>(null);
  // Por que o formulário não salvou. Antes ele só não fazia nada.
  const [erroForm, setErroForm] = useState('');

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
          const cru = JSON.parse(eventos);
          if (Array.isArray(cru)) {
            // Conserta de uma vez os eventos gravados com o fim inflado
            const { lista, mudou } = corrigirIndices(cru);
            setEventosSalvos(lista);
            if (mudou) await AsyncStorage.setItem(CHAVE_EVENTOS, JSON.stringify(lista));
          }
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
    setErroForm('');
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
    setErroForm('');
    setEventoSelecionado(null);
    setIsFormVisible(true);
  };

  const fecharForm = () => {
    setIsFormVisible(false);
    setEditandoEvento(null);
    setNovoEventoNome('');
    setErroForm('');
  };

  const salvarEventoNaPlanilha = () => {
    // Estes três casos faziam `return` calado: o usuário apertava SALVAR,
    // nada acontecia, e não havia como saber se o botão estava quebrado ou
    // se ele tinha digitado algo errado. Agora cada um diz o que houve.
    if (!horaInicio || !minInicio || !horaFim || !minFim) {
      setErroForm('Preencha as quatro casas de horário (início e fim).');
      return;
    }

    const inicioIdx = obterIndiceHorario(horaInicio, minInicio, false);
    const fimIdx    = obterIndiceHorario(horaFim, minFim, true);

    if (inicioIdx === -1 || fimIdx === -1) {
      setErroForm('Horário inválido — use de 00:00 até 23:59.');
      return;
    }
    if (inicioIdx >= fimIdx) {
      setErroForm('O fim precisa ser pelo menos 30 minutos depois do início.');
      return;
    }
    setErroForm('');

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

  /**
   * Excluir passou a ter duas etapas.
   *
   * O botão "excluir" fica a 6px do "editar", os dois com 12px de ícone e
   * 3px de respiro — um alvo de uns 20px de altura, menos da metade do
   * mínimo de 44. Encostar no errado era fácil, e o evento sumia na hora,
   * sem aviso e sem volta. Agora o toque só abre a pergunta.
   */
  const pedirExclusao = () => {
    if (!eventoSelecionado) return;
    setConfirmandoExclusao(eventoSelecionado);
  };

  const confirmarExclusao = () => {
    const alvo = confirmandoExclusao;
    setConfirmandoExclusao(null);
    if (!alvo) return;
    const novaLista = eventosSalvos.filter(e => e.id !== alvo.id);
    setEventosSalvos(novaLista);
    salvarEventosNoStorage(novaLista);
    setEventoSelecionado(null);
  };

  const modoEdicao = editandoEvento !== null;

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>

      {/* HEADER */}
      <View style={[styles.header, { backgroundColor: theme.headerBg }]}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}
          onPress={() => navigation.navigate('EnemEnade')}
          style={[styles.iconButton, { backgroundColor: theme.iconButtonBg }]}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <Ionicons name="arrow-back" size={24} color={theme.textPrimary} />
        </TouchableOpacity>
        <TouchableOpacity accessibilityRole="button" style={styles.rowCenter} onPress={() => navigation.navigate('MeusDados')}>
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
              <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={fecharForm}
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
                <TouchableOpacity accessibilityRole="button"
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
                <TouchableOpacity accessibilityRole="button"
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

            {!!erroForm && (
              <Text style={styles.erroForm} accessibilityRole="alert">{erroForm}</Text>
            )}

            <TouchableOpacity
              style={[styles.saveButton, modoEdicao && styles.saveButtonEdit]}
              onPress={salvarEventoNaPlanilha}
              accessibilityRole="button"
              accessibilityLabel={modoEdicao ? 'Atualizar o evento' : 'Salvar o evento'}
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
                  <Text style={[styles.headerText, { color: theme.roxoCabecalho },
                                index === 0 && { color: theme.textSecondary }]}>{dia}</Text>
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
                        /*
                          Papel de botão SÓ na célula que tem evento.
                          São 336 células na grade; marcar todas faria o leitor
                          de tela anunciar "botão" trezentas e trinta e seis
                          vezes para atravessar a semana. Célula vazia não faz
                          nada mesmo — o onPress só age quando há evento.
                        */
                        accessibilityRole={ev ? 'button' : undefined}
                        accessibilityLabel={ev
                          ? `${ev.nome}, ${ev.dia}, ${ev.horaStr}${isSelected ? ', selecionado' : ''}`
                          : undefined}
                        accessibilityState={ev ? { selected: !!isSelected } : undefined}
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
                          /*
                            Só a hora de INÍCIO na célula.
                            "09:00 - 11:00" não cabe nos 60px da coluna: sobra
                            9px, o que corta exatamente um caractere e mostra
                            "09:00 - 11:0…" — uma hora truncada é pior de ler
                            do que uma hora curta e completa. O intervalo
                            inteiro continua no cartão do evento selecionado.
                          */
                          <Text numberOfLines={1}
                                style={[styles.eventSlotText,
                                        { color: corDoTextoSobre(ev.cor),
                                          textShadowColor: sombraDoTextoSobre(ev.cor) }]}>
                            {(ev.horaStr || '').split(' - ')[0] || ev.horaStr}
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
                        hitSlop={{ top: 10, bottom: 10, left: 6, right: 4 }}
                        accessibilityRole="button"
                        accessibilityLabel={`Editar o evento ${eventoSelecionado.nome}`}
                      >
                        <Ionicons name="pencil-outline" size={13} color="#FFF" />
                        <Text style={styles.actionButtonText}>editar</Text>
                      </TouchableOpacity>
                      {/* Excluir */}
                      <TouchableOpacity
                        onPress={pedirExclusao}
                        style={styles.deleteButton}
                        hitSlop={{ top: 10, bottom: 10, left: 4, right: 6 }}
                        accessibilityRole="button"
                        accessibilityLabel={`Excluir o evento ${eventoSelecionado.nome}`}
                      >
                        <Ionicons name="trash-outline" size={13} color="#FFF" />
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
         <TouchableOpacity accessibilityRole="button" style={styles.navItem}>
           <Ionicons name="calendar-outline" size={24} color={theme.roxoAtivo} />
           <Text style={[styles.navText, { color: theme.roxoAtivo }]}>Cronograma</Text>
         </TouchableOpacity>
       
         {/* LIVROS  */}
         <TouchableOpacity accessibilityRole="button" onPress={() => navigation.navigate('LivrosEnade')} style={styles.navItem}>
           <Ionicons name="book-outline" size={24} color={isDarkMode ? "#D1D5DB" : "#4B5563"} />
           <Text style={[styles.navText, { color: theme.navInactive }]}>Livros</Text>
         </TouchableOpacity>
       
         {/* MATÉRIAS */}
         <TouchableOpacity accessibilityRole="button" onPress={() => navigation.navigate('materia')} style={styles.navItem}>
           <Ionicons name="school-outline" size={24} color={isDarkMode ? "#D1D5DB" : "#4B5563"} />
           <Text style={[styles.navText, { color: theme.navInactive }]}>Matérias</Text>
         </TouchableOpacity>
         {/* SIMULADOS  */}
         <TouchableOpacity accessibilityRole="button" onPress={() => navigation.navigate('SimuladosDashboard')} style={styles.navItem}>
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

      {/* Confirmação de exclusão — apagar um evento não tem desfazer. */}
      <Modal transparent visible={!!confirmandoExclusao} animationType="fade"
             onRequestClose={() => setConfirmandoExclusao(null)}>
        <View style={{
          flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
          justifyContent: 'center', padding: 28,
        }}>
          <View style={{ backgroundColor: theme.card, borderRadius: 16, padding: 22 }}>
            <Text style={{ color: theme.textPrimary, fontSize: 17, fontWeight: '700' }}>
              Excluir este evento?
            </Text>

            <View style={{
              flexDirection: 'row', alignItems: 'center', marginTop: 14,
              paddingLeft: 10, borderLeftWidth: 3,
              borderLeftColor: confirmandoExclusao?.cor ?? theme.border,
            }}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: theme.textPrimary, fontSize: 14, fontWeight: '600' }}
                      numberOfLines={2}>
                  {confirmandoExclusao?.nome}
                </Text>
                <Text style={{ color: theme.textSecondary, fontSize: 12, marginTop: 2 }}>
                  {confirmandoExclusao?.dia} · {confirmandoExclusao?.horaStr}
                </Text>
              </View>
            </View>

            <Text style={{ color: theme.textSecondary, fontSize: 12, marginTop: 14 }}>
              Não dá para desfazer.
            </Text>

            <View style={{ flexDirection: 'row', justifyContent: 'flex-end', marginTop: 20 }}>
              <TouchableOpacity
                onPress={() => setConfirmandoExclusao(null)}
                style={{ height: 48, paddingHorizontal: 18, justifyContent: 'center', marginRight: 8 }}
                accessibilityRole="button"
                accessibilityLabel="Cancelar e manter o evento"
              >
                <Text style={{ color: theme.textSecondary, fontWeight: '600' }}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={confirmarExclusao}
                style={{
                  backgroundColor: '#EF4444', borderRadius: 10,
                  height: 48, paddingHorizontal: 22, justifyContent: 'center',
                }}
                accessibilityRole="button"
                accessibilityLabel="Confirmar a exclusão do evento"
              >
                <Text style={{ color: '#FFF', fontWeight: '700' }}>Excluir</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
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
  floatingBottomContainer: { position: 'absolute', bottom: 0, width: width, borderTopLeftRadius: 15, borderTopRightRadius: 15, zIndex: 1000, elevation: 10 },
  fabButton: { position: 'absolute', right: 20, bottom: 200, backgroundColor: '#FBBF24', width: 46, height: 46, borderRadius: 23, justifyContent: 'center', alignItems: 'center', zIndex: 1001, elevation: 11 },
  eventsContainer: { paddingHorizontal: 15, paddingTop: 10, paddingBottom: 10 },
  sectionTitle: { fontSize: 10, fontWeight: 'bold', marginBottom: 5 },
  eventCard: { flexDirection: 'row', borderRadius: 12, padding: 10, alignItems: 'center', borderLeftWidth: 3 },
  iconBox: { width: 30, height: 30, borderRadius: 8, justifyContent: 'center', alignItems: 'center', marginRight: 10 },
  eventInfo: { flex: 1 },
  eventHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  eventTitle: { fontSize: 12, fontWeight: 'bold', flex: 1 },
  // O gap maior e os 30px de altura separam "editar" de "excluir". Com o
  // hitSlop de 10 em cima e embaixo, a área de toque chega a 50px — antes
  // eram uns 20, e os dois botões quase se encostavam.
  actionButtons: { flexDirection: 'row', gap: 12 },
  editButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, backgroundColor: '#6A5AE0', paddingHorizontal: 10, minHeight: 30, borderRadius: 6 },
  deleteButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 4, backgroundColor: '#EF4444', paddingHorizontal: 10, minHeight: 30, borderRadius: 6 },
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
  erroForm: { color: '#EF4444', fontSize: 11, marginBottom: 8, lineHeight: 15 },
  saveButton: { backgroundColor: '#6A5AE0', padding: 10, borderRadius: 8, alignItems: 'center' },
  saveButtonEdit: { backgroundColor: '#F59E0B' },
  saveButtonText: { color: '#FFF', fontSize: 12, fontWeight: 'bold' },

  /*== NAVEGAÇÃO ==*/
  bottomNav: { flexDirection: 'row', justifyContent: 'space-around', paddingVertical: 20, paddingBottom: 25, borderTopWidth: 1 },
  navItem: { alignItems: 'center' },
  navText: { fontSize: 9, marginTop: 5 },
});
