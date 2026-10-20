// ============================================================
//  NIVELIS — Tela de Matérias (Expo Router + TypeScript)
//  Usa fetch nativo (sem axios)
// ============================================================
//
//  ONDE COLOCAR:
//    app/materias.tsx
//
//  COMO NAVEGAR ATÉ AQUI:
//    import { router } from 'expo-router'
//    router.push('/materias')
// ============================================================

import React, { useState, useEffect } from 'react'
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  TextInput, ActivityIndicator, Alert, LayoutAnimation,
  UIManager, Platform,
} from 'react-native'
import { router, Stack } from 'expo-router'

if (Platform.OS === 'android' && UIManager.setLayoutAnimationEnabledExperimental) {
  UIManager.setLayoutAnimationEnabledExperimental(true)
}

const API_URL = 'http://10.0.2.2:8001'

const C = {
  bg:      '#09090f',
  bg2:     '#111119',
  bg3:     '#1a1a26',
  card:    '#13131e',
  card2:   '#1c1c2a',
  purple:  '#7c3aed',
  purpleL: '#9d62f5',
  accent:  '#a78bfa',
  text:    '#f0eeff',
  text2:   '#9188b8',
  text3:   '#4e4870',
  border:  '#252338',
  green:   '#22c55e',
  red:     '#ef4444',
}

interface MateriaConfig { nome: string; ico: string; cor: string }

const MATERIAS_CONFIG: Record<string, MateriaConfig> = {
  portugues:   { nome:'Português',   ico:'📖', cor:'#4f46e5' },
  matematica:  { nome:'Matemática',  ico:'➕', cor:'#7c3aed' },
  atualidades: { nome:'Atualidades', ico:'🌍', cor:'#0891b2' },
  filosofia:   { nome:'Filosofia',   ico:'🧠', cor:'#b45309' },
  sociologia:  { nome:'Sociologia',  ico:'👥', cor:'#059669' },
}

interface Topico {
  id?:             string
  topico:          string
  total_questoes?: number
}

interface Alternativas { A:string; B:string; C:string; D:string; E:string }

interface Exercicio {
  numero:       number
  contexto?:    string
  enunciado:    string
  alternativas: Alternativas
}

interface ItemGabarito {
  numero:           number
  resposta_correta: string
  resposta_usuario: string
  acertou:          boolean
  explicacao:       string
}

interface ResultadoExerc {
  sessao_id:      string
  acertos:        number
  erros:          number
  total:          number
  aproveitamento: string
  gabarito:       ItemGabarito[]
}

interface Conteudo {
  materia:           string
  topico:            string
  resumo:            string
  conceitos_chave:   string[]
  exemplo_resolvido: {
    enunciado:               string
    resolucao_passo_a_passo: string
  } | null
  total_questoes:    number
}

interface ExercicioCardProps {
  questao:             Exercicio
  respostaSelecionada: string | undefined
  onSelecionar:        (num: number, letra: string) => void
  gabarito?:           ItemGabarito
  corrigido:           boolean
}

function ExercicioCard({ questao, respostaSelecionada, onSelecionar, gabarito, corrigido }: ExercicioCardProps) {
  const correta = gabarito?.resposta_correta

  return (
    <View style={styles.questaoCard}>
      <Text style={styles.qNum}>Exercício {questao.numero}</Text>
      {questao.contexto ? (
        <Text style={styles.qContexto}>🏷 {questao.contexto}</Text>
      ) : null}
      <Text style={styles.qEnunciado}>{questao.enunciado}</Text>

      {Object.entries(questao.alternativas || {}).map(([letra, texto]) => {
        let estilo: any   = styles.alternativa
        let letraEst: any = styles.altLetra

        if (corrigido) {
          if (letra === correta) {
            estilo   = [styles.alternativa, styles.altCorreta]
            letraEst = [styles.altLetra, { backgroundColor:C.green, borderColor:C.green }]
          } else if (letra === respostaSelecionada && letra !== correta) {
            estilo   = [styles.alternativa, styles.altErrada]
            letraEst = [styles.altLetra, { backgroundColor:C.red, borderColor:C.red }]
          }
        } else if (letra === respostaSelecionada) {
          estilo   = [styles.alternativa, styles.altSelecionada]
          letraEst = [styles.altLetra, { borderColor:C.purple }]
        }

        return (
          <TouchableOpacity
            key={letra}
            style={estilo}
            onPress={() => !corrigido && onSelecionar(questao.numero, letra)}
            activeOpacity={corrigido ? 1 : 0.7}
          >
            <View style={letraEst}>
              <Text style={{ color:C.text, fontWeight:'700', fontSize:11 }}>{letra}</Text>
            </View>
            <Text style={styles.altTexto}>{texto as string}</Text>
          </TouchableOpacity>
        )
      })}

      {corrigido && gabarito?.explicacao ? (
        <View style={styles.explicacaoBox}>
          <Text style={styles.explicacaoTxt}>{gabarito.explicacao}</Text>
        </View>
      ) : null}
    </View>
  )
}

interface TopicoScreenProps {
  materia:  string
  topico:   string
  onVoltar: () => void
}

function TopicoView({ materia, topico, onVoltar }: TopicoScreenProps) {
  const [conteudo,   setConteudo]   = useState<Conteudo | null>(null)
  const [carregando, setCarregando] = useState(true)
  const [exercicios, setExercicios] = useState<Exercicio[]>([])
  const [sessaoId,   setSessaoId]   = useState<string | null>(null)
  const [respostas,  setRespostas]  = useState<Record<number, string>>({})
  const [gabarito,   setGabarito]   = useState<Record<number, ItemGabarito> | null>(null)
  const [resultado,  setResultado]  = useState<ResultadoExerc | null>(null)
  const [corrigido,  setCorrigido]  = useState(false)
  const [loadExerc,  setLoadExerc]  = useState(false)
  const [corrigindo, setCorrigindo] = useState(false)

  const topicoSlug = topico.toLowerCase().replace(/ /g, '_')

  useEffect(() => { carregarConteudo() }, [topico])

  async function carregarConteudo() {
    setCarregando(true)
    try {
      const response = await fetch(`${API_URL}/conteudo/${materia}/${topicoSlug}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data: Conteudo = await response.json()
      setConteudo(data)
    } catch (e: any) {
      Alert.alert('Erro', 'Conteúdo não encontrado.\nRode popular_banco.py primeiro.')
    } finally {
      setCarregando(false)
    }
  }

  async function carregarExercicios() {
    setLoadExerc(true)
    setExercicios([])
    setRespostas({})
    setGabarito(null)
    setResultado(null)
    setCorrigido(false)
    setSessaoId(null)

    try {
      const response = await fetch(
        `${API_URL}/exercicios/${materia}/${topicoSlug}?quantidade=3`
      )
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      setExercicios(data.questoes)
      setSessaoId(data.sessao_id)
    } catch (e: any) {
      Alert.alert('Erro', 'Nenhum exercício disponível para este tópico.')
    } finally {
      setLoadExerc(false)
    }
  }

  async function corrigirExercicios() {
    if (!sessaoId) return
    setCorrigindo(true)

    const respostasStr: Record<string, string> = {}
    Object.entries(respostas).forEach(([k,v]) => { respostasStr[String(k)] = v })

    try {
      const response = await fetch(`${API_URL}/exercicios/${sessaoId}/resultado`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ respostas: respostasStr }),
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data: ResultadoExerc = await response.json()
      const gabMap: Record<number, ItemGabarito> = {}
      data.gabarito.forEach(g => { gabMap[g.numero] = g })
      setGabarito(gabMap)
      setResultado(data)
      setCorrigido(true)
    } catch (e: any) {
      Alert.alert('Erro', 'Não foi possível corrigir.')
    } finally {
      setCorrigindo(false)
    }
  }

  function selecionarResposta(num: number, letra: string) {
    setRespostas(prev => ({ ...prev, [num]: letra }))
  }

  const totalResp    = Object.keys(respostas).length
  const podeCorrigir = totalResp === exercicios.length && exercicios.length > 0

  if (carregando) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity style={styles.backBtn} onPress={onVoltar}>
            <Text style={styles.backArrow}>‹</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle} numberOfLines={1}>{topico}</Text>
          <View style={styles.avatar}><Text style={styles.avatarTxt}>R</Text></View>
        </View>
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={C.purple} size="large"/>
          <Text style={styles.loadingTxt}>Carregando conteúdo...</Text>
        </View>
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={onVoltar}>
          <Text style={styles.backArrow}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{topico}</Text>
        <View style={styles.avatar}><Text style={styles.avatarTxt}>R</Text></View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom:40 }}>

        {conteudo && (
          <>
            <View style={styles.secTitle}>
              <View style={styles.secIcon}><Text>📖</Text></View>
              <Text style={styles.secTitleTxt}>Resumo</Text>
            </View>

            <View style={styles.resumoCard}>
              <Text style={styles.resumoTxt}>{conteudo.resumo}</Text>
            </View>

            {conteudo.conceitos_chave?.length > 0 && (
              <>
                <View style={styles.secTitle}>
                  <View style={styles.secIcon}><Text>🔑</Text></View>
                  <Text style={styles.secTitleTxt}>Conceitos-chave</Text>
                </View>
                <View style={styles.conceitosWrap}>
                  {conteudo.conceitos_chave.map((c, i) => (
                    <View key={i} style={styles.conceitoTag}>
                      <Text style={styles.conceitoTxt}>{c}</Text>
                    </View>
                  ))}
                </View>
              </>
            )}

            {conteudo.exemplo_resolvido && (
              <>
                <View style={styles.secTitle}>
                  <View style={styles.secIcon}><Text>📌</Text></View>
                  <Text style={styles.secTitleTxt}>Exemplo Resolvido</Text>
                </View>
                <View style={styles.exemploCard}>
                  <Text style={styles.exemploEnunciado}>
                    {conteudo.exemplo_resolvido.enunciado}
                  </Text>
                  <Text style={styles.exemploResolucao}>
                    {conteudo.exemplo_resolvido.resolucao_passo_a_passo}
                  </Text>
                </View>
              </>
            )}
          </>
        )}

        <View style={styles.secTitle}>
          <View style={styles.secIcon}><Text>📝</Text></View>
          <Text style={styles.secTitleTxt}>Praticar</Text>
        </View>

        {exercicios.length === 0 ? (
          <TouchableOpacity
            style={[styles.btnPrimary, { marginHorizontal:20, justifyContent:'center' }, loadExerc && { opacity:.5 }]}
            onPress={carregarExercicios}
            disabled={loadExerc}
          >
            {loadExerc
              ? <ActivityIndicator color="#fff" size="small"/>
              : <Text style={styles.btnTxt}>Iniciar Exercícios ▶</Text>
            }
          </TouchableOpacity>
        ) : (
          <>
            {resultado && (
              <View style={[styles.resultadoCard, { marginBottom:16 }]}>
                <Text style={styles.resultadoTitulo}>📊 Resultado</Text>
                <View style={styles.resultadoStats}>
                  <View style={styles.resStat}>
                    <Text style={[styles.resVal, { color:C.green }]}>{resultado.acertos}</Text>
                    <Text style={styles.resLbl}>Acertos</Text>
                  </View>
                  <View style={styles.resStat}>
                    <Text style={[styles.resVal, { color:C.red }]}>{resultado.erros}</Text>
                    <Text style={styles.resLbl}>Erros</Text>
                  </View>
                  <View style={styles.resStat}>
                    <Text style={[styles.resVal, { color:C.accent }]}>{resultado.aproveitamento}</Text>
                    <Text style={styles.resLbl}>Aproveitamento</Text>
                  </View>
                </View>
              </View>
            )}

            {exercicios.map(q => (
              <ExercicioCard
                key={q.numero}
                questao={q}
                respostaSelecionada={respostas[q.numero]}
                onSelecionar={selecionarResposta}
                gabarito={gabarito?.[q.numero]}
                corrigido={corrigido}
              />
            ))}

            <View style={styles.acoesBtns}>
              {!corrigido && (
                <TouchableOpacity
                  style={[styles.btnPrimary, !podeCorrigir && { opacity:.4 }]}
                  onPress={corrigirExercicios}
                  disabled={!podeCorrigir || corrigindo}
                >
                  {corrigindo
                    ? <ActivityIndicator color="#fff" size="small"/>
                    : <Text style={styles.btnTxt}>✅ Ver Gabarito</Text>
                  }
                </TouchableOpacity>
              )}
              <TouchableOpacity style={styles.btnOutline} onPress={carregarExercicios}>
                <Text style={styles.btnOutlineTxt}>↺ Novos Exercícios</Text>
              </TouchableOpacity>
            </View>
          </>
        )}

      </ScrollView>
    </View>
  )
}

interface TopicoAberto { materia: string; topico: string }

export default function MateriasScreen() {
  const [materias,     setMaterias]     = useState<string[]>([])
  const [topicosMap,   setTopicosMap]   = useState<Record<string, Topico[]>>({})
  const [abertas,      setAbertas]      = useState<Record<string, boolean>>({})
  const [busca,        setBusca]        = useState('')
  const [carregando,   setCarregando]   = useState(true)
  const [topicoAberto, setTopicoAberto] = useState<TopicoAberto | null>(null)

  useEffect(() => { carregarMaterias() }, [])

  async function carregarMaterias() {
    setCarregando(true)
    try {
      const response = await fetch(`${API_URL}/materias`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      const lista: string[] = data.materias || Object.keys(MATERIAS_CONFIG)
      setMaterias(lista)

      const map: Record<string, Topico[]> = {}
      await Promise.all(lista.map(async mat => {
        try {
          const resp = await fetch(`${API_URL}/topicos/${mat}`)
          if (resp.ok) {
            const dt = await resp.json()
            map[mat] = dt.topicos || []
          } else {
            map[mat] = []
          }
        } catch {
          map[mat] = []
        }
      }))
      setTopicosMap(map)

    } catch {
      setMaterias(Object.keys(MATERIAS_CONFIG))
    } finally {
      setCarregando(false)
    }
  }

  function toggleMateria(matId: string) {
    LayoutAnimation.configureNext(LayoutAnimation.Presets.easeInEaseOut)
    setAbertas(prev => ({ ...prev, [matId]: !prev[matId] }))
  }

  const materiasFiltradas = materias.filter(m => {
    const cfg = MATERIAS_CONFIG[m]
    return cfg?.nome.toLowerCase().includes(busca.toLowerCase()) || !busca
  })

  if (topicoAberto) {
    return (
      <>
        <Stack.Screen options={{ headerShown: false }}/>
        <TopicoView
          materia={topicoAberto.materia}
          topico={topicoAberto.topico}
          onVoltar={() => setTopicoAberto(null)}
        />
      </>
    )
  }

  return (
    <View style={styles.container}>

      <Stack.Screen options={{ headerShown: false }}/>

      <View style={styles.header}>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backArrow}>‹</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Matérias</Text>
        <View style={styles.avatar}><Text style={styles.avatarTxt}>R</Text></View>
      </View>

      <View style={styles.searchBar}>
        <Text style={{ fontSize:16 }}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          placeholder="Buscar matérias..."
          placeholderTextColor={C.text3}
          value={busca}
          onChangeText={setBusca}
        />
      </View>

      {carregando ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={C.purple} size="large"/>
          <Text style={styles.loadingTxt}>Carregando matérias...</Text>
        </View>
      ) : (
        <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ paddingBottom:40 }}>
          {materiasFiltradas.map(matId => {
            const cfg     = MATERIAS_CONFIG[matId] || { nome:matId, ico:'📚', cor:C.purple }
            const topicos = topicosMap[matId] || []
            const aberta  = abertas[matId]

            return (
              <View key={matId} style={[styles.materiaGroup, aberta && styles.materiaAberta]}>

                <TouchableOpacity style={styles.materiaHdr} onPress={() => toggleMateria(matId)}>
                  <View style={[styles.matIco, { backgroundColor: cfg.cor }]}>
                    <Text style={{ fontSize:17 }}>{cfg.ico}</Text>
                  </View>
                  <Text style={styles.matNome}>{cfg.nome}</Text>
                  <Text style={styles.chevron}>{aberta ? '▲' : '▼'}</Text>
                </TouchableOpacity>

                {aberta && (
                  <View style={styles.materiaBody}>
                    {topicos.length > 0 ? (
                      topicos.map((t, i) => (
                        <TouchableOpacity
                          key={i}
                          style={styles.lesson}
                          onPress={() => setTopicoAberto({ materia: matId, topico: t.topico })}
                        >
                          <View style={styles.lessonPlay}>
                            <Text style={{ color:'#fff', fontSize:8 }}>▶</Text>
                          </View>
                          <Text style={styles.lessonNome}>{t.topico}</Text>
                          <Text style={styles.lessonDur}>{t.total_questoes || 0} questões</Text>
                        </TouchableOpacity>
                      ))
                    ) : (
                      <View style={styles.emptyState}>
                        <Text style={styles.emptyIco}>📭</Text>
                        <Text style={styles.emptyTxt}>
                          Nenhum tópico ainda.{'\n'}Rode popular_banco.py primeiro.
                        </Text>
                      </View>
                    )}
                  </View>
                )}

              </View>
            )
          })}
        </ScrollView>
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container:   { flex:1, backgroundColor: C.bg },

  header:      { flexDirection:'row', alignItems:'center', justifyContent:'space-between',
                  paddingTop:52, paddingHorizontal:20, paddingBottom:14,
                  backgroundColor:C.bg, borderBottomWidth:1, borderBottomColor:'rgba(255,255,255,.04)' },
  backBtn:     { width:36, height:36, borderRadius:18, backgroundColor:C.card2,
                  borderWidth:1, borderColor:C.border, alignItems:'center', justifyContent:'center' },
  backArrow:   { color:C.text, fontSize:22, lineHeight:26 },
  headerTitle: { color:C.text, fontSize:17, fontWeight:'700', flex:1, textAlign:'center' },
  avatar:      { width:36, height:36, borderRadius:18, backgroundColor:C.purple,
                  alignItems:'center', justifyContent:'center',
                  borderWidth:2, borderColor:C.purpleL },
  avatarTxt:   { color:'#fff', fontWeight:'800', fontSize:14 },

  searchBar:   { flexDirection:'row', alignItems:'center', gap:10,
                  marginHorizontal:20, marginBottom:18, marginTop:14,
                  backgroundColor:C.card, borderRadius:14,
                  borderWidth:1, borderColor:C.border, padding:12 },
  searchInput: { flex:1, color:C.text, fontSize:13 },

  materiaGroup: { marginHorizontal:20, marginBottom:10, backgroundColor:C.card,
                   borderRadius:14, overflow:'hidden',
                   borderWidth:1, borderColor:C.border },
  materiaAberta:{ borderColor:'rgba(124,58,237,.4)' },
  materiaHdr:  { flexDirection:'row', alignItems:'center', gap:12, padding:14 },
  matIco:      { width:38, height:38, borderRadius:11,
                  alignItems:'center', justifyContent:'center' },
  matNome:     { color:C.text, fontWeight:'700', fontSize:15, flex:1 },
  chevron:     { color:C.text3, fontSize:12 },

  materiaBody: { borderTopWidth:1, borderTopColor:C.border },

  lesson:      { flexDirection:'row', alignItems:'center', gap:10,
                  padding:12, paddingHorizontal:14,
                  borderTopWidth:1, borderTopColor:'rgba(255,255,255,.04)' },
  lessonPlay:  { width:20, height:20, borderRadius:10, backgroundColor:C.purple,
                  alignItems:'center', justifyContent:'center' },
  lessonNome:  { color:C.text, fontSize:13, flex:1 },
  lessonDur:   { color:C.text3, fontSize:11 },

  emptyState:  { alignItems:'center', padding:24, gap:8 },
  emptyIco:    { fontSize:32, opacity:.4 },
  emptyTxt:    { color:C.text3, fontSize:12, textAlign:'center', lineHeight:18 },

  loadingWrap: { flex:1, alignItems:'center', justifyContent:'center', gap:14 },
  loadingTxt:  { color:C.text3, fontSize:13 },

  secTitle:    { flexDirection:'row', alignItems:'center', gap:8,
                  paddingHorizontal:20, marginBottom:12, marginTop:6 },
  secIcon:     { width:22, height:22, backgroundColor:'rgba(124,58,237,.18)',
                  borderRadius:6, alignItems:'center', justifyContent:'center' },
  secTitleTxt: { color:C.text, fontWeight:'700', fontSize:14 },

  resumoCard:  { marginHorizontal:20, marginBottom:14, backgroundColor:C.card,
                  borderRadius:14, borderWidth:1, borderColor:C.border, padding:16 },
  resumoTxt:   { color:C.text2, fontSize:13, lineHeight:21 },

  conceitosWrap:{ flexDirection:'row', flexWrap:'wrap', paddingHorizontal:20, marginBottom:14, gap:6 },
  conceitoTag: { backgroundColor:'rgba(124,58,237,.15)', borderRadius:20,
                  borderWidth:1, borderColor:'rgba(124,58,237,.3)',
                  paddingHorizontal:10, paddingVertical:4 },
  conceitoTxt: { color:C.accent, fontSize:11, fontWeight:'600' },

  exemploCard: { marginHorizontal:20, marginBottom:14, backgroundColor:C.card,
                  borderRadius:14, borderLeftWidth:3, borderLeftColor:C.purple,
                  borderWidth:1, borderColor:C.border, padding:14 },
  exemploEnunciado: { color:C.text, fontSize:13, fontWeight:'600',
                       marginBottom:10, lineHeight:20 },
  exemploResolucao: { color:C.text2, fontSize:12, lineHeight:19 },

  questaoCard: { marginHorizontal:20, marginBottom:14, backgroundColor:C.card2,
                  borderRadius:14, padding:14, borderWidth:1, borderColor:C.border },
  qNum:        { color:C.accent, fontSize:10, fontWeight:'700',
                  letterSpacing:.8, textTransform:'uppercase', marginBottom:4 },
  qContexto:   { color:C.accent, fontSize:10, marginBottom:8,
                  fontStyle:'italic', opacity:.8 },
  qEnunciado:  { color:C.text, fontSize:13, lineHeight:20, marginBottom:12 },
  alternativa: { flexDirection:'row', alignItems:'flex-start', gap:10,
                  padding:9, borderRadius:8, marginBottom:4,
                  borderWidth:1, borderColor:'transparent' },
  altSelecionada: { backgroundColor:'rgba(124,58,237,.2)', borderColor:C.purple },
  altCorreta:     { backgroundColor:'rgba(34,197,94,.15)',  borderColor:C.green },
  altErrada:      { backgroundColor:'rgba(239,68,68,.12)',  borderColor:C.red },
  altLetra:    { width:24, height:24, borderRadius:12,
                  backgroundColor:C.bg3, borderWidth:1, borderColor:C.border,
                  alignItems:'center', justifyContent:'center' },
  altTexto:    { color:C.text, fontSize:12, lineHeight:18, flex:1 },
  explicacaoBox:  { marginTop:10, padding:10,
                    backgroundColor:'rgba(124,58,237,.08)',
                    borderLeftWidth:3, borderLeftColor:C.purple, borderRadius:6 },
  explicacaoTxt:  { color:C.text2, fontSize:12, lineHeight:18 },

  resultadoCard:  { marginHorizontal:20, backgroundColor:C.card,
                    borderRadius:14, padding:16,
                    borderWidth:1, borderColor:C.purple },
  resultadoTitulo:{ color:C.accent, fontWeight:'700', fontSize:14, marginBottom:12 },
  resultadoStats: { flexDirection:'row', gap:10 },
  resStat:     { flex:1, backgroundColor:C.bg3, borderRadius:10,
                  padding:10, alignItems:'center' },
  resVal:      { fontWeight:'800', fontSize:20, marginBottom:2 },
  resLbl:      { color:C.text2, fontSize:10, textTransform:'uppercase', letterSpacing:.5 },

  acoesBtns:   { flexDirection:'row', gap:10, marginHorizontal:20,
                  marginTop:8, marginBottom:24, flexWrap:'wrap' },

  btnPrimary:  { backgroundColor:C.purple, paddingHorizontal:18, paddingVertical:11,
                  borderRadius:10, alignItems:'center', justifyContent:'center',
                  flexDirection:'row', gap:6,
                  shadowColor:C.purple, shadowOffset:{width:0,height:4},
                  shadowOpacity:.4, shadowRadius:8, elevation:4 },
  btnTxt:      { color:'#fff', fontWeight:'700', fontSize:13 },
  btnOutline:  { borderWidth:1, borderColor:C.border, paddingHorizontal:16,
                  paddingVertical:11, borderRadius:10, alignItems:'center', justifyContent:'center' },
  btnOutlineTxt:{ color:C.text2, fontWeight:'600', fontSize:13 },
})
