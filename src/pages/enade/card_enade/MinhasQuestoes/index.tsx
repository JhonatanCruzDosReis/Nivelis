// ─────────────────────────────────────────────────────────────────────────────
//  MINHAS QUESTÕES — criar, revisar e excluir
//
//  Lista o que o usuário escreveu e abre o formulário de criação/edição.
//  As questões ficam no aparelho; nada sobe para a API.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, ScrollView, StatusBar,
  KeyboardAvoidingView, Platform, ActivityIndicator, Modal,
} from 'react-native';
import { MaterialIcons, Feather } from '@expo/vector-icons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';

import { useTheme } from '../../../TemasAcoes/Temas';
import NivelisModal, { useNivelisModal } from '../../../../components/NivelisModal';
import {
  listar, criar, atualizar, excluir, validar,
  LETRAS, type MinhaQuestao, type RascunhoQuestao, type ErroValidacao,
} from '../../../../services/minhasQuestoesService';

const MATERIAS_SUGERIDAS = [
  'Matemática', 'Linguagens', 'Humanas', 'Natureza',
  'Redes de Computadores', 'Análise e Desenvolvimento de Sistemas',
  'Direito', 'Administração',
];

const RASCUNHO_VAZIO: RascunhoQuestao = {
  materia: '', topico: '', enunciado: '',
  alternativas: ['', '', '', '', ''], gabarito: '', explicacao: '', tipo: 'ENADE',
};

/**
 * Dois rascunhos são iguais?
 *
 * Campo a campo, incluindo as cinco alternativas. É o que decide se o X
 * fecha direto ou se vale a pena perguntar: quem abriu o editor e não
 * escreveu nada não merece um diálogo no caminho, e quem escreveu
 * trinta linhas não merece perdê-las num toque.
 */
const mesmoRascunho = (a: RascunhoQuestao, b: RascunhoQuestao): boolean =>
  a.materia    === b.materia    &&
  a.topico     === b.topico     &&
  a.enunciado  === b.enunciado  &&
  a.gabarito   === b.gabarito   &&
  a.explicacao === b.explicacao &&
  a.tipo       === b.tipo       &&
  a.alternativas.length === b.alternativas.length &&
  a.alternativas.every((t, i) => t === b.alternativas[i]);

export default function MinhasQuestoesScreen() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();
  const { modal, showModal } = useNivelisModal();

  const [lista, setLista]           = useState<MinhaQuestao[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [editorAberto, setEditor]   = useState(false);
  const [editandoId, setEditandoId] = useState<string | null>(null);
  const [rascunho, setRascunho]     = useState<RascunhoQuestao>(RASCUNHO_VAZIO);
  const [erros, setErros]           = useState<ErroValidacao[]>([]);
  const [salvando, setSalvando]     = useState(false);
  const [confirmar, setConfirmar]   = useState<MinhaQuestao | null>(null);

  // Como o rascunho estava quando o editor abriu. É a régua do "mudou algo?".
  const [original, setOriginal]     = useState<RascunhoQuestao>(RASCUNHO_VAZIO);
  const [perguntarSaida, setPerguntarSaida] = useState(false);

  // Navegação que foi interceptada (botão voltar / gesto) e espera resposta.
  const acaoPendente = useRef<any>(null);
  // Quando true, deixa a navegação passar em vez de interceptar de novo.
  const saindoRef    = useRef(false);

  const sujo = editorAberto && !mesmoRascunho(rascunho, original);

  const theme = {
    bg:      isDarkMode ? '#000000' : '#F5F5F7',
    card:    isDarkMode ? '#121214' : '#FFFFFF',
    cardSec: isDarkMode ? '#18181B' : '#F0F0F0',
    text:    isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:     isDarkMode ? '#A1A1AA' : '#666666',
    border:  isDarkMode ? '#27272A' : '#E5E5E5',
    // Fundo de botão com texto branco: #EC4899 dava 3.53:1. 16% mais
    // escuro, o branco passa a 4.81:1.
    primary: '#C63C81',
    // O mesmo rosa em versão legível sobre o próprio tom claro (selos).
    primaryTxt: isDarkMode ? '#EC4899' : '#9D174D',
    success: '#10B981',
    danger:  '#EF4444',
  };

  const recarregar = useCallback(async () => {
    try {
      setLista(await listar());
    } finally {
      setCarregando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { recarregar(); }, [recarregar]));

  const erroDe = (campo: ErroValidacao['campo']) =>
    erros.find(e => e.campo === campo)?.mensagem;

  const abrirNova = () => {
    setEditandoId(null);
    setRascunho(RASCUNHO_VAZIO);
    setOriginal(RASCUNHO_VAZIO);
    setErros([]);
    setEditor(true);
  };

  const abrirEdicao = (q: MinhaQuestao) => {
    const textos = ['', '', '', '', ''];
    q.alternativas.forEach(a => {
      const i = LETRAS.indexOf(a.id as any);
      if (i >= 0) textos[i] = a.texto;
    });
    const comoVeio: RascunhoQuestao = {
      materia:      q.materia,
      topico:       q.topico ?? '',
      enunciado:    q.enunciado,
      alternativas: textos,
      gabarito:     q.gabarito ?? '',
      explicacao:   q.explicacao ?? '',
      tipo:         q.tipo ?? 'ENADE',
    };
    setEditandoId(q.id);
    setRascunho(comoVeio);
    // Editando, a régua é a questão como ela está salva — não o rascunho
    // vazio. Abrir e fechar sem tocar em nada não pode pedir confirmação.
    setOriginal(comoVeio);
    setErros([]);
    setEditor(true);
  };

  // ── Sair do editor ────────────────────────────────────────────────────────
  //
  //  O X descartava tudo num toque. A tela já pergunta antes de EXCLUIR uma
  //  questão salva ("não dá para desfazer"), mas jogava fora sem perguntar
  //  a questão que o usuário acabou de escrever e ainda não salvou — que é
  //  exatamente o trabalho mais fácil de perder e o mais caro de refazer.
  //
  //  `acao` é a navegação interceptada: null quando o toque foi no X (aí é
  //  só fechar o editor e voltar para a lista), ou o evento do botão voltar
  //  do Android / gesto do iOS, que precisa ser reemitido depois.

  const fecharEditorAgora = (acao: any = null) => {
    setPerguntarSaida(false);
    setEditor(false);
    setRascunho(RASCUNHO_VAZIO);
    setOriginal(RASCUNHO_VAZIO);
    setErros([]);
    acaoPendente.current = null;
    if (acao) {
      saindoRef.current = true;
      navigation.dispatch(acao);
    }
  };

  const tentarSair = (acao: any = null) => {
    if (!sujo) { fecharEditorAgora(acao); return; }
    acaoPendente.current = acao;
    setPerguntarSaida(true);
  };

  // Botão voltar do Android e gesto de voltar do iOS passam por aqui. Sem
  // isso o guarda cobriria só o X, e a porta mais usada ficaria aberta.
  useEffect(() => {
    const inscricao = navigation.addListener('beforeRemove', (e: any) => {
      if (!sujo || saindoRef.current) return;
      e.preventDefault();
      acaoPendente.current = e.data.action;
      setPerguntarSaida(true);
    });
    return inscricao;
  }, [navigation, sujo]);

  /**
   * `saindo` vem do diálogo de saída. Nesse caminho o usuário já pediu para
   * ir embora, então a questão é salva e a navegação interceptada segue —
   * sem o aviso de sucesso, que ele não ficaria para ler.
   *
   * Se a validação reprovar, NÃO sai: o editor continua aberto com os erros
   * em vermelho. Sair levando o rascunho junto seria o bug de novo, só que
   * disfarçado de "salvar".
   */
  const salvar = async ({ saindo = false }: { saindo?: boolean } = {}) => {
    const problemas = validar(rascunho);
    setErros(problemas);
    if (problemas.length) {
      if (saindo) {
        showModal('Falta preencher',
                  'A questão não pôde ser salva ainda — veja o que está marcado em vermelho.',
                  'error');
      }
      return;
    }

    setSalvando(true);
    try {
      if (editandoId) {
        await atualizar(editandoId, rascunho);
        if (!saindo) showModal('Salvo ✅', 'Sua questão foi atualizada.', 'success');
      } else {
        await criar(rascunho);
        if (!saindo) showModal('Criada ✅', 'Sua questão já entra no praticar.', 'success');
      }
      const acao = acaoPendente.current;
      fecharEditorAgora(saindo ? acao : null);
      await recarregar();
    } catch (e: any) {
      showModal('Erro', e?.message ?? 'Não foi possível salvar.', 'error');
    } finally {
      setSalvando(false);
    }
  };

  const confirmarExclusao = async () => {
    if (!confirmar) return;
    const alvo = confirmar;
    setConfirmar(null);
    try {
      await excluir(alvo.id);
      await recarregar();
      showModal('Excluída', 'A questão foi removida.', 'success');
    } catch {
      showModal('Erro', 'Não foi possível excluir.', 'error');
    }
  };

  const mudarAlternativa = (i: number, txt: string) => {
    const alts = [...rascunho.alternativas];
    alts[i] = txt;
    setRascunho({ ...rascunho, alternativas: alts });
  };

  // ── EDITOR ────────────────────────────────────────────────────────────────
  if (editorAberto) {
    return (
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1, backgroundColor: theme.bg }}
      >
        <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

        <View style={{
          flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
          paddingHorizontal: 16, paddingTop: 50, paddingBottom: 12,
        }}>
          <TouchableOpacity onPress={() => tentarSair()}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            accessibilityRole="button"
            accessibilityLabel="Fechar o editor"
          >
            <MaterialIcons name="close" size={26} color={theme.text} />
          </TouchableOpacity>
          <Text style={{ color: theme.text, fontSize: 17, fontWeight: '700' }}>
            {editandoId ? 'Editar questão' : 'Nova questão'}
          </Text>
          <View style={{ width: 26 }} />
        </View>

        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
          {/* Tipo */}
          <Text style={{ color: theme.sub, fontSize: 13, marginBottom: 6 }}>Prova</Text>
          <View style={{ flexDirection: 'row', marginBottom: 16 }}>
            {(['ENEM', 'ENADE'] as const).map(t => (
              <TouchableOpacity accessibilityRole="button"
                key={t}
                onPress={() => setRascunho({ ...rascunho, tipo: t })}
                style={{
                  paddingVertical: 8, paddingHorizontal: 18, borderRadius: 20, marginRight: 8,
                  borderWidth: 1,
                  borderColor: rascunho.tipo === t ? theme.primary : theme.border,
                  backgroundColor: rascunho.tipo === t ? theme.primary : 'transparent',
                }}
              >
                <Text style={{
                  color: rascunho.tipo === t ? '#FFF' : theme.sub, fontWeight: '600', fontSize: 13,
                }}>{t}</Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Matéria */}
          <Text style={{ color: theme.sub, fontSize: 13, marginBottom: 6 }}>Matéria</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginBottom: 8 }}>
            {MATERIAS_SUGERIDAS.map(m => (
              <TouchableOpacity accessibilityRole="button"
                key={m}
                onPress={() => setRascunho({ ...rascunho, materia: m })}
                style={{
                  paddingVertical: 7, paddingHorizontal: 14, borderRadius: 16, marginRight: 8,
                  borderWidth: 1,
                  borderColor: rascunho.materia === m ? theme.primary : theme.border,
                  backgroundColor: rascunho.materia === m ? `${theme.primary}22` : 'transparent',
                }}
              >
                <Text style={{
                  color: rascunho.materia === m ? theme.primaryTxt : theme.sub, fontSize: 12,
                }}>{m}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
          <TextInput
            value={rascunho.materia}
            onChangeText={t => setRascunho({ ...rascunho, materia: t })}
            placeholder="ou digite outra matéria"
            placeholderTextColor={theme.sub}
            style={{
              backgroundColor: theme.card, color: theme.text, borderRadius: 10,
              borderWidth: 1, borderColor: erroDe('materia') ? theme.danger : theme.border,
              padding: 12, marginBottom: 4,
            }}
          />
          {!!erroDe('materia') && (
            <Text style={{ color: theme.danger, fontSize: 12, marginBottom: 8 }}>{erroDe('materia')}</Text>
          )}

          {/* Tópico */}
          <Text style={{ color: theme.sub, fontSize: 13, marginTop: 12, marginBottom: 6 }}>
            Tópico (opcional)
          </Text>
          <TextInput
            value={rascunho.topico}
            onChangeText={t => setRascunho({ ...rascunho, topico: t })}
            placeholder="Ex.: ponto de equilíbrio"
            placeholderTextColor={theme.sub}
            style={{
              backgroundColor: theme.card, color: theme.text, borderRadius: 10,
              borderWidth: 1, borderColor: theme.border, padding: 12,
            }}
          />

          {/* Enunciado */}
          <Text style={{ color: theme.sub, fontSize: 13, marginTop: 16, marginBottom: 6 }}>
            Enunciado
          </Text>
          <TextInput
            value={rascunho.enunciado}
            onChangeText={t => setRascunho({ ...rascunho, enunciado: t })}
            placeholder="Escreva a pergunta"
            placeholderTextColor={theme.sub}
            multiline
            style={{
              backgroundColor: theme.card, color: theme.text, borderRadius: 10,
              borderWidth: 1, borderColor: erroDe('enunciado') ? theme.danger : theme.border,
              padding: 12, minHeight: 100, textAlignVertical: 'top',
            }}
          />
          {!!erroDe('enunciado') && (
            <Text style={{ color: theme.danger, fontSize: 12, marginTop: 4 }}>{erroDe('enunciado')}</Text>
          )}

          {/* Alternativas */}
          <Text style={{ color: theme.sub, fontSize: 13, marginTop: 16, marginBottom: 6 }}>
            Alternativas — toque na letra para marcar a correta
          </Text>
          {LETRAS.map((letra, i) => {
            const correta = rascunho.gabarito === letra;
            return (
              <View key={letra} style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                <TouchableOpacity accessibilityRole="button"
                  onPress={() => setRascunho({ ...rascunho, gabarito: letra })}
                  style={{
                    width: 38, height: 38, borderRadius: 19, marginRight: 10,
                    alignItems: 'center', justifyContent: 'center', borderWidth: 1.5,
                    borderColor: correta ? theme.success : theme.border,
                    backgroundColor: correta ? theme.success : 'transparent',
                  }}
                >
                  <Text style={{ color: correta ? '#FFF' : theme.sub, fontWeight: '700' }}>{letra}</Text>
                </TouchableOpacity>
                <TextInput
                  value={rascunho.alternativas[i]}
                  onChangeText={t => mudarAlternativa(i, t)}
                  placeholder={i < 2 ? `Alternativa ${letra}` : `Alternativa ${letra} (opcional)`}
                  placeholderTextColor={theme.sub}
                  multiline
                  style={{
                    flex: 1, backgroundColor: theme.card, color: theme.text, borderRadius: 10,
                    borderWidth: 1,
                    borderColor: correta ? theme.success : theme.border,
                    padding: 10,
                  }}
                />
              </View>
            );
          })}
          {!!erroDe('alternativas') && (
            <Text style={{ color: theme.danger, fontSize: 12 }}>{erroDe('alternativas')}</Text>
          )}
          {!!erroDe('gabarito') && (
            <Text style={{ color: theme.danger, fontSize: 12 }}>{erroDe('gabarito')}</Text>
          )}

          {/* Explicação */}
          <Text style={{ color: theme.sub, fontSize: 13, marginTop: 16, marginBottom: 6 }}>
            Por que essa é a resposta (opcional)
          </Text>
          <TextInput
            value={rascunho.explicacao}
            onChangeText={t => setRascunho({ ...rascunho, explicacao: t })}
            placeholder="Aparece depois que você responde"
            placeholderTextColor={theme.sub}
            multiline
            style={{
              backgroundColor: theme.card, color: theme.text, borderRadius: 10,
              borderWidth: 1, borderColor: theme.border, padding: 12,
              minHeight: 80, textAlignVertical: 'top',
            }}
          />

          <TouchableOpacity accessibilityRole="button"
            onPress={() => salvar()}
            disabled={salvando}
            style={{
              backgroundColor: theme.primary, borderRadius: 12, padding: 16,
              alignItems: 'center', marginTop: 24, opacity: salvando ? 0.7 : 1,
            }}
          >
            {salvando
              ? <ActivityIndicator color="#FFF" />
              : <Text style={{ color: '#FFF', fontWeight: '700', fontSize: 15 }}>
                  {editandoId ? 'Salvar alterações' : 'Criar questão'}
                </Text>}
          </TouchableOpacity>
        </ScrollView>

        {/*
          Guarda de saída.

          Os três botões ficam EMPILHADOS, um por linha. Em 390px de
          largura, três botões lado a lado estouram — foi o que aconteceu
          com o "Salvar e sair" do simulado, que quebrou em duas linhas e
          só apareceu quando a tela foi renderizada de verdade. Empilhado
          não tem esse risco e ainda dá 48px de altura de toque em cada um.
        */}
        <Modal transparent visible={perguntarSaida} animationType="fade"
               onRequestClose={() => setPerguntarSaida(false)}>
          <View style={{
            flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
            justifyContent: 'center', padding: 28,
          }}>
            <View style={{ backgroundColor: theme.card, borderRadius: 16, padding: 22 }}>
              <Text style={{ color: theme.text, fontSize: 17, fontWeight: '700' }}>
                {editandoId ? 'Descartar as alterações?' : 'Descartar esta questão?'}
              </Text>
              <Text style={{ color: theme.sub, marginTop: 10, lineHeight: 20 }}>
                {editandoId
                  ? 'Você mudou esta questão e ainda não salvou. Se sair agora, ela volta a ser como estava.'
                  : 'Você escreveu esta questão e ainda não salvou. Se sair agora, ela se perde.'}
              </Text>

              <TouchableOpacity
                onPress={() => { setPerguntarSaida(false); salvar({ saindo: true }); }}
                style={{
                  backgroundColor: theme.primary, borderRadius: 12,
                  height: 48, alignItems: 'center', justifyContent: 'center',
                  marginTop: 20,
                }}
                accessibilityRole="button"
                accessibilityLabel="Salvar a questão e sair"
              >
                <Text style={{ color: '#FFF', fontWeight: '700', fontSize: 15 }}>Salvar</Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => { acaoPendente.current = null; setPerguntarSaida(false); }}
                style={{
                  borderRadius: 12, height: 48, marginTop: 8,
                  alignItems: 'center', justifyContent: 'center',
                  borderWidth: 1, borderColor: theme.border,
                }}
                accessibilityRole="button"
                accessibilityLabel={editandoId ? 'Continuar editando' : 'Continuar escrevendo'}
              >
                <Text style={{ color: theme.text, fontWeight: '600', fontSize: 15 }}>
                  {editandoId ? 'Continuar editando' : 'Continuar escrevendo'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                onPress={() => fecharEditorAgora(acaoPendente.current)}
                style={{
                  borderRadius: 12, height: 48, marginTop: 8,
                  alignItems: 'center', justifyContent: 'center',
                }}
                accessibilityRole="button"
                accessibilityLabel="Descartar e sair sem salvar"
              >
                <Text style={{ color: theme.danger, fontWeight: '600', fontSize: 15 }}>
                  Descartar
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>

        <NivelisModal {...modal} />
      </KeyboardAvoidingView>
    );
  }

  // ── LISTA ─────────────────────────────────────────────────────────────────
  return (
    <View style={{ flex: 1, backgroundColor: theme.bg }}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      <View style={{
        flexDirection: 'row', alignItems: 'center',
        paddingHorizontal: 16, paddingTop: 50, paddingBottom: 12,
      }}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <MaterialIcons name="arrow-back" size={26} color={theme.text} />
        </TouchableOpacity>
        <Text style={{ color: theme.text, fontSize: 18, fontWeight: '700', marginLeft: 14 }}>
          Minhas questões
        </Text>
      </View>

      {carregando ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator color={theme.primary} />
        </View>
      ) : lista.length === 0 ? (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 }}>
          <Feather name="edit-3" size={42} color={theme.sub} />
          <Text style={{ color: theme.text, fontSize: 16, fontWeight: '600', marginTop: 14 }}>
            Nenhuma questão sua ainda
          </Text>
          <Text style={{ color: theme.sub, textAlign: 'center', marginTop: 8, lineHeight: 20 }}>
            Escreva as suas próprias questões — elas aparecem no praticar junto
            com as demais, e ficam salvas só neste aparelho.
          </Text>
        </View>
      ) : (
        <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 100 }}>
          <Text style={{ color: theme.sub, fontSize: 13, marginBottom: 12 }}>
            {lista.length} {lista.length === 1 ? 'questão' : 'questões'}
          </Text>

          {lista.map(q => (
            <View
              key={q.id}
              style={{
                backgroundColor: theme.card, borderRadius: 12, borderWidth: 1,
                borderColor: theme.border, padding: 14, marginBottom: 12,
              }}
            >
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                <View style={{
                  backgroundColor: `${theme.primary}22`, paddingHorizontal: 8,
                  paddingVertical: 3, borderRadius: 8,
                }}>
                  <Text style={{ color: theme.primaryTxt, fontSize: 11, fontWeight: '600' }}>
                    {q.materia}
                  </Text>
                </View>
                {!!q.tipo && (
                  <Text style={{ color: theme.sub, fontSize: 11, marginLeft: 8 }}>{q.tipo}</Text>
                )}
              </View>

              <Text style={{ color: theme.text, lineHeight: 20 }} numberOfLines={3}>
                {q.enunciado}
              </Text>

              <Text style={{ color: theme.success, fontSize: 12, marginTop: 8, fontWeight: '600' }}>
                Gabarito: {q.gabarito}
              </Text>

              <View style={{
                flexDirection: 'row', marginTop: 12, borderTopWidth: 1,
                borderTopColor: theme.border, paddingTop: 10,
              }}>
                <TouchableOpacity accessibilityRole="button"
                  onPress={() => abrirEdicao(q)}
                  style={{ flexDirection: 'row', alignItems: 'center', marginRight: 20 }}
                >
                  <Feather name="edit-2" size={15} color={theme.sub} />
                  <Text style={{ color: theme.sub, marginLeft: 6, fontSize: 13 }}>Editar</Text>
                </TouchableOpacity>

                <TouchableOpacity accessibilityRole="button"
                  onPress={() => setConfirmar(q)}
                  style={{ flexDirection: 'row', alignItems: 'center' }}
                >
                  <Feather name="trash-2" size={15} color={theme.danger} />
                  <Text style={{ color: theme.danger, marginLeft: 6, fontSize: 13 }}>Excluir</Text>
                </TouchableOpacity>
              </View>
            </View>
          ))}
        </ScrollView>
      )}

      {/* Botão flutuante */}
      <TouchableOpacity accessibilityRole="button"
        onPress={abrirNova}
        style={{
          position: 'absolute', right: 20, bottom: 28,
          backgroundColor: theme.primary, borderRadius: 28,
          paddingHorizontal: 20, paddingVertical: 15,
          flexDirection: 'row', alignItems: 'center',
          shadowColor: '#000', shadowOpacity: 0.3, shadowRadius: 8,
          shadowOffset: { width: 0, height: 4 }, elevation: 6,
        }}
      >
        <MaterialIcons name="add" size={20} color="#FFF" />
        <Text style={{ color: '#FFF', fontWeight: '700', marginLeft: 6 }}>Nova</Text>
      </TouchableOpacity>

      {/* Confirmação de exclusão — excluir é irreversível, então pergunta. */}
      <Modal transparent visible={!!confirmar} animationType="fade"
             onRequestClose={() => setConfirmar(null)}>
        <View style={{
          flex: 1, backgroundColor: 'rgba(0,0,0,0.6)',
          justifyContent: 'center', padding: 32,
        }}>
          <View style={{ backgroundColor: theme.card, borderRadius: 16, padding: 22 }}>
            <Text style={{ color: theme.text, fontSize: 17, fontWeight: '700' }}>
              Excluir esta questão?
            </Text>
            <Text style={{ color: theme.sub, marginTop: 10, lineHeight: 20 }} numberOfLines={3}>
              {confirmar?.enunciado}
            </Text>
            <Text style={{ color: theme.sub, marginTop: 10, fontSize: 12 }}>
              Não dá para desfazer.
            </Text>

            <View style={{ flexDirection: 'row', justifyContent: 'flex-end', marginTop: 20 }}>
              <TouchableOpacity accessibilityRole="button" onPress={() => setConfirmar(null)} style={{ padding: 12, marginRight: 8 }}>
                <Text style={{ color: theme.sub, fontWeight: '600' }}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity accessibilityRole="button"
                onPress={confirmarExclusao}
                style={{ backgroundColor: theme.danger, borderRadius: 10, paddingHorizontal: 20, paddingVertical: 12 }}
              >
                <Text style={{ color: '#FFF', fontWeight: '700' }}>Excluir</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <NivelisModal {...modal} />
    </View>
  );
}
