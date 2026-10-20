// ─────────────────────────────────────────────────────────────────────────────
//  MONTAR — escolhe o conteúdo e o tamanho, e sai para um dos dois destinos
//
//  Esta tela é o único lugar do app que dá acesso ao catálogo procedural.
//  Sem ela, /procedural/topicos, os grupos e o maximo_sugerido não tinham
//  consumidor: a cascata usava disciplina fixa no código.
//
//  Ela NÃO monta o caderno. Ela junta os parâmetros e navega — quem busca é
//  a tela de destino, que é a mesma de sempre. Assim existe uma implementação
//  só de cronômetro, correção e gabarito.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useState, useEffect, useMemo } from 'react';
import {
  View, Text, TouchableOpacity, ScrollView, StatusBar, ActivityIndicator,
} from 'react-native';
import { MaterialIcons, Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';

import CarregandoLento from '../../../../components/CarregandoLento';
import { useTheme } from '../../../TemasAcoes/Temas';
import { proceduralApi, type CatalogoProcedural } from '../../../../services/apiService';

type Prova = 'ENEM' | 'ENADE';

/**
 * O que cada prova oferece.
 *
 * O procedural cobre ENEM só em português e matemática — os dois geradores
 * de matemática não se sobrepõem, então os dois entram. Humanas e natureza
 * não existem, e a tela diz isso em vez de fingir que a lista está completa.
 */
const CONTEUDO_POR_PROVA: Record<Prova, string[]> = {
  ENEM:  ['enem', 'portugues', 'basica', 'matematica'],
  ENADE: ['computacao', 'concursos', 'medicina', 'medicina_basico',
          'ads', 'redes', 'engenharia', 'direito', 'administracao', 'saude',
          'anatomia', 'fisiologia', 'bioquimica', 'biocelular', 'histologia',
          'embriologia', 'genetica', 'imunologia', 'microbiologia', 'farmacologia'],
};

const ROTULOS: Record<string, string> = {
  enem:            'ENEM completo',
  fundamental:     'Fundamental',
  computacao:      'Computação (tudo)',
  concursos:       'Concursos (tudo)',
  medicina:        'Medicina (ciclo básico)',
  medicina_basico: 'Medicina (básico reduzido)',
  portugues:       'Português',
  basica:          'Matemática básica',
  matematica:      'Matemática (combinatória e probabilidade)',
  ads:             'Análise e Desenvolvimento de Sistemas',
  redes:           'Redes de Computadores',
  engenharia:      'Engenharia de Software',
  direito:         'Direito',
  administracao:   'Administração',
  saude:           'Saúde',
  anatomia:        'Anatomia',
  fisiologia:      'Fisiologia',
  bioquimica:      'Bioquímica',
  biocelular:      'Biologia Celular',
  histologia:      'Histologia',
  embriologia:     'Embriologia',
  genetica:        'Genética',
  imunologia:      'Imunologia',
  microbiologia:   'Microbiologia',
  farmacologia:    'Farmacologia',
};

const rotulo = (chave: string) =>
  ROTULOS[chave] ?? chave.charAt(0).toUpperCase() + chave.slice(1).replace(/_/g, ' ');

const QUANTIDADES = [5, 10, 20, 30, 45, 60, 90];
const MINUTOS_POR_QUESTAO = [2, 3, 4, 5];

export default function MontarSimuladoScreen() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [catalogo, setCatalogo]   = useState<CatalogoProcedural | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [prova, setProva]         = useState<Prova>('ENADE');
  const [escolha, setEscolha]     = useState<string>('');
  const [topico, setTopico]       = useState<string>('');
  const [quantidade, setQuant]    = useState(20);
  const [minPorQuestao, setMin]   = useState(3);

  const theme = {
    bg:      isDarkMode ? '#000000' : '#F5F5F7',
    card:    isDarkMode ? '#121214' : '#FFFFFF',
    text:    isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:     isDarkMode ? '#A1A1AA' : '#666666',
    border:  isDarkMode ? '#27272A' : '#E5E5E5',
    primary: '#4F46E5',
    warn:    '#F59E0B',
  };

  useEffect(() => {
    (async () => {
      setCatalogo(await proceduralApi.topicos());
      setCarregando(false);
    })();
  }, []);

  // Só oferece o que a prova cobre E o servidor realmente carregou: gerador
  // ausente não pode virar chip que devolve caderno vazio.
  const opcoes = useMemo(() => {
    if (!catalogo) return [];
    const disponiveis = new Set([
      ...catalogo.disciplinas.map(d => d.chave),
      ...Object.keys(catalogo.grupos),
    ]);
    return CONTEUDO_POR_PROVA[prova].filter(c => disponiveis.has(c));
  }, [catalogo, prova]);

  useEffect(() => { setEscolha(opcoes[0] ?? ''); setTopico(''); }, [opcoes]);

  const ehGrupo = !!catalogo?.grupos[escolha];

  const topicosDaEscolha = useMemo(() => {
    if (!catalogo || !escolha || ehGrupo) return [];
    return catalogo.disciplinas.find(d => d.chave === escolha)?.topicos ?? [];
  }, [catalogo, escolha, ehGrupo]);

  // O teto do material escolhido. É o que impede o "pedi 30 e vieram 6".
  const teto = catalogo?.maximoSugerido[escolha] ?? 30;
  const quantidadesValidas = QUANTIDADES.filter(q => q <= teto);
  const quantidadeFinal = Math.min(quantidade, teto);
  const duracao = quantidadeFinal * minPorQuestao;

  // Se a escolha mudou para algo mais magro, desce a quantidade junto.
  useEffect(() => {
    if (quantidade > teto) setQuant(quantidadesValidas[quantidadesValidas.length - 1] ?? teto);
  }, [teto]);

  const irPraticar = () => {
    navigation.navigate('Questoes', {
      proceduralDisciplina: escolha,
      proceduralTopico:     topico || undefined,
      proceduralQuantidade: Math.min(quantidadeFinal, 20),
      tipo:                 prova,
    });
  };

  const irSimulado = () => {
    navigation.navigate('SimuladoAndamento', {
      proceduralDisciplinas: escolha,
      proceduralQuantidade:  quantidadeFinal,
      proceduralMinutos:     duracao,
      tipo:                  prova,
    });
  };

  const Chip = ({ ativo, onPress, children, small }: any) => (
    <TouchableOpacity accessibilityRole="button"
      onPress={onPress}
      style={{
        paddingVertical: small ? 6 : 9,
        paddingHorizontal: small ? 12 : 15,
        borderRadius: 18, marginRight: 8, marginBottom: 8, borderWidth: 1,
        borderColor: ativo ? theme.primary : theme.border,
        backgroundColor: ativo ? `${theme.primary}22` : theme.card,
      }}
    >
      <Text style={{
        color: ativo ? theme.primary : theme.sub,
        fontSize: small ? 12 : 13,
        fontWeight: ativo ? '700' : '500',
      }}>{children}</Text>
    </TouchableOpacity>
  );

  if (carregando) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.bg }}>
        <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
        <CarregandoLento
          titulo="Vendo o que dá para montar"
          tema={theme}
          onCancelar={() => navigation.goBack()}
          rotuloCancelar="Voltar"
        />
      </View>
    );
  }

  if (!catalogo || opcoes.length === 0) {
    return (
      <View style={{ flex: 1, backgroundColor: theme.bg }}>
        <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />
        <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: 50, paddingBottom: 12 }}>
          <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => navigation.goBack()}
            accessibilityRole="button"
            accessibilityLabel="Voltar"
          >
            <MaterialIcons name="arrow-back" size={26} color={theme.text} />
          </TouchableOpacity>
          <Text style={{ color: theme.text, fontSize: 18, fontWeight: '700', marginLeft: 14 }}>Montar</Text>
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', padding: 32 }}>
          <Ionicons name="cloud-offline-outline" size={40} color={theme.sub} />
          <Text style={{ color: theme.text, fontWeight: '600', marginTop: 14, textAlign: 'center' }}>
            Catálogo indisponível
          </Text>
          <Text style={{ color: theme.sub, textAlign: 'center', marginTop: 8, lineHeight: 20 }}>
            Não foi possível falar com o servidor de questões. Os simulados
            prontos continuam funcionando.
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, backgroundColor: theme.bg }}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingTop: 50, paddingBottom: 12 }}>
        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => navigation.goBack()}
          accessibilityRole="button"
          accessibilityLabel="Voltar"
        >
          <MaterialIcons name="arrow-back" size={26} color={theme.text} />
        </TouchableOpacity>
        <Text style={{ color: theme.text, fontSize: 18, fontWeight: '700', marginLeft: 14 }}>
          Montar questões
        </Text>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
        {/* PROVA */}
        <Text style={{ color: theme.sub, fontSize: 13, marginBottom: 8 }}>Prova</Text>
        <View style={{ flexDirection: 'row' }}>
          {(['ENEM', 'ENADE'] as Prova[]).map(p => (
            <Chip key={p} ativo={prova === p} onPress={() => setProva(p)}>{p}</Chip>
          ))}
        </View>

        {prova === 'ENEM' && (
          <View style={{
            flexDirection: 'row', backgroundColor: `${theme.warn}18`, borderRadius: 10,
            padding: 11, marginTop: 4, marginBottom: 4,
          }}>
            <Ionicons name="information-circle-outline" size={17} color={theme.warn} />
            <Text style={{ color: theme.sub, fontSize: 12, marginLeft: 8, flex: 1, lineHeight: 17 }}>
              O gerador cobre português e matemática. Humanas e natureza ainda
              não têm questões próprias.
            </Text>
          </View>
        )}

        {/* CONTEÚDO */}
        <Text style={{ color: theme.sub, fontSize: 13, marginTop: 16, marginBottom: 8 }}>
          Conteúdo
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
          {opcoes.map(c => (
            <Chip key={c} ativo={escolha === c} onPress={() => { setEscolha(c); setTopico(''); }}>
              {rotulo(c)}
            </Chip>
          ))}
        </View>

        {ehGrupo && (
          <Text style={{ color: theme.sub, fontSize: 12, marginTop: 2, lineHeight: 17 }}>
            Reúne {catalogo.grupos[escolha].map(rotulo).join(', ')}.
          </Text>
        )}

        {/* TÓPICO */}
        {topicosDaEscolha.length > 1 && (
          <>
            <Text style={{ color: theme.sub, fontSize: 13, marginTop: 18, marginBottom: 8 }}>
              Tópico (opcional)
            </Text>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
              <Chip small ativo={!topico} onPress={() => setTopico('')}>Todos</Chip>
              {topicosDaEscolha.map(t => (
                <Chip key={t.chave} small ativo={topico === t.chave} onPress={() => setTopico(t.chave)}>
                  {t.rotulo}
                </Chip>
              ))}
            </View>
          </>
        )}

        {/* QUANTIDADE */}
        <Text style={{ color: theme.sub, fontSize: 13, marginTop: 18, marginBottom: 8 }}>
          Quantas questões
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
          {quantidadesValidas.map(q => (
            <Chip key={q} ativo={quantidadeFinal === q} onPress={() => setQuant(q)}>{q}</Chip>
          ))}
        </View>

        {/* O teto vem medido do servidor: é quantos fatos distintos a
            disciplina sustenta antes de começar a repetir. */}
        <Text style={{ color: theme.sub, fontSize: 12, lineHeight: 17 }}>
          {teto < 30
            ? `Este conteúdo sustenta até ${teto} questões sem repetir. ` +
              `Para um caderno maior, escolha um grupo.`
            : `Este conteúdo sustenta até ${teto} questões sem repetir.`}
        </Text>

        {/* TEMPO */}
        <Text style={{ color: theme.sub, fontSize: 13, marginTop: 18, marginBottom: 8 }}>
          Ritmo do cronômetro
        </Text>
        <View style={{ flexDirection: 'row', flexWrap: 'wrap' }}>
          {MINUTOS_POR_QUESTAO.map(m => (
            <Chip key={m} small ativo={minPorQuestao === m} onPress={() => setMin(m)}>
              {m} min/questão
            </Chip>
          ))}
        </View>
        <Text style={{ color: theme.sub, fontSize: 12 }}>
          {quantidadeFinal} questões × {minPorQuestao} min = {' '}
          <Text style={{ color: theme.text, fontWeight: '700' }}>
            {Math.floor(duracao / 60) > 0 ? `${Math.floor(duracao / 60)}h` : ''}
            {duracao % 60 > 0 ? `${duracao % 60}min` : ''}
          </Text>
        </Text>

        {/* AÇÕES */}
        <TouchableOpacity accessibilityRole="button"
          onPress={irSimulado}
          style={{
            backgroundColor: theme.primary, borderRadius: 12, padding: 16,
            alignItems: 'center', marginTop: 26, flexDirection: 'row',
            justifyContent: 'center',
          }}
        >
          <Ionicons name="timer-outline" size={19} color="#FFF" />
          <Text style={{ color: '#FFF', fontWeight: '700', fontSize: 15, marginLeft: 8 }}>
            Simulado cronometrado
          </Text>
        </TouchableOpacity>

        <TouchableOpacity accessibilityRole="button"
          onPress={irPraticar}
          style={{
            borderRadius: 12, padding: 16, alignItems: 'center', marginTop: 10,
            borderWidth: 1, borderColor: theme.border, flexDirection: 'row',
            justifyContent: 'center',
          }}
        >
          <Ionicons name="school-outline" size={19} color={theme.text} />
          <Text style={{ color: theme.text, fontWeight: '600', fontSize: 15, marginLeft: 8 }}>
            Praticar sem tempo
          </Text>
        </TouchableOpacity>

        <Text style={{ color: theme.sub, fontSize: 11, textAlign: 'center', marginTop: 14, lineHeight: 16 }}>
          {/* A frase antiga terminava em "não consomem cota de IA". Cota é
              problema de quem paga a conta, não de quem estuda; para o
              usuário, o que importa é que a resposta é confiável. */}
          As questões são geradas na hora, e a resposta é calculada — não
          chutada.
        </Text>
      </ScrollView>
    </View>
  );
}
