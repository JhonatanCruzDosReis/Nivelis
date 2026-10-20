import React, { useState } from 'react';
import {
  StyleSheet, Text, View, TouchableOpacity,
  ScrollView, ActivityIndicator, StatusBar,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import {
  collection, getDocs, deleteDoc, doc,
} from 'firebase/firestore';
import { db } from '../../../../services/firebase';
import { useTheme } from '../../../TemasAcoes/Temas';

/**
 * TELA TEMPORARIA DE LIMPEZA
 *
 * Remove do Firestore os "simulados fantasmas" (sem questoes).
 * USE UMA VEZ e depois remova esta tela e a rota.
 *
 * Como acessar: adicione temporariamente um botao em alguma tela:
 *   navigation.navigate('LimpezaBanco')
 */
export default function LimpezaBancoScreen() {
  const navigation = useNavigation<any>();
  const { isDarkMode } = useTheme();

  const [analisando, setAnalisando] = useState(false);
  const [limpando,   setLimpando]   = useState(false);
  const [relatorio,  setRelatorio]  = useState<{
    total: number;
    comQuestoes: number;
    vazios: number;
    idsVazios: string[];
  } | null>(null);
  const [resultado, setResultado] = useState<string | null>(null);

  const theme = {
    bg:      isDarkMode ? '#000000' : '#F5F5F7',
    card:    isDarkMode ? '#15151C' : '#FFFFFF',
    text:    isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:     isDarkMode ? '#A1A1AA' : '#666666',
    border:  isDarkMode ? '#27272A' : '#E5E5E5',
    primary: '#8B5CF6',
    danger:  '#EF4444',
    success: '#10B981',
    warning: '#F59E0B',
  };

  // Passo 1: analisar (so conta, nao apaga)
  const analisar = async () => {
    setAnalisando(true);
    setResultado(null);
    try {
      const snap = await getDocs(collection(db, 'simulados'));
      const idsVazios: string[] = [];
      let comQuestoes = 0;

      snap.forEach((d: any) => {
        const data = d.data();
        const temQ = Array.isArray(data.questoes) && data.questoes.length > 0;
        const totalQ = data.total_questoes ?? 0;
        if (temQ || totalQ > 0) {
          comQuestoes++;
        } else {
          idsVazios.push(d.id);
        }
      });

      setRelatorio({
        total: snap.size,
        comQuestoes,
        vazios: idsVazios.length,
        idsVazios,
      });
    } catch (e: any) {
      setResultado('Erro ao analisar: ' + e.message);
    } finally {
      setAnalisando(false);
    }
  };

  // Passo 2: limpar (apaga os vazios)
  const limpar = async () => {
    if (!relatorio || relatorio.idsVazios.length === 0) return;
    setLimpando(true);
    setResultado(null);
    let apagados = 0;
    let erros = 0;

    for (const id of relatorio.idsVazios) {
      try {
        await deleteDoc(doc(db, 'simulados', id));
        apagados++;
      } catch {
        erros++;
      }
    }

    setResultado(`✅ ${apagados} simulados vazios apagados. ${erros > 0 ? `(${erros} erros)` : ''}`);
    setRelatorio(null);
    setLimpando(false);
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} />

      {/* HEADER */}
      <View style={[styles.header, { borderBottomColor: theme.border }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.iconButton}>
          <Ionicons name="arrow-back" size={24} color={theme.text} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.text }]}>Limpeza do Banco</Text>
        <View style={{ width: 30 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={[styles.warnBox, { backgroundColor: theme.warning + '15', borderColor: theme.warning }]}>
          <Ionicons name="warning-outline" size={24} color={theme.warning} />
          <Text style={[styles.warnText, { color: theme.text }]}>
            Esta tela remove simulados SEM questões do banco. Use uma vez e depois remova a tela.
          </Text>
        </View>

        {/* PASSO 1 */}
        <Text style={[styles.stepTitle, { color: theme.text }]}>Passo 1: Analisar</Text>
        <TouchableOpacity
          style={[styles.btn, { backgroundColor: theme.primary }, analisando && { opacity: 0.6 }]}
          onPress={analisar}
          disabled={analisando || limpando}
        >
          {analisando
            ? <ActivityIndicator color="#FFF" />
            : <Text style={styles.btnText}>Analisar Banco</Text>}
        </TouchableOpacity>

        {/* RELATORIO */}
        {relatorio && (
          <View style={[styles.card, { backgroundColor: theme.card, borderColor: theme.border }]}>
            <Text style={[styles.cardTitle, { color: theme.text }]}>Relatório</Text>
            <View style={styles.row}>
              <Text style={[styles.label, { color: theme.sub }]}>Total no banco:</Text>
              <Text style={[styles.value, { color: theme.text }]}>{relatorio.total}</Text>
            </View>
            <View style={styles.row}>
              <Text style={[styles.label, { color: theme.success }]}>✓ Com questões:</Text>
              <Text style={[styles.value, { color: theme.success }]}>{relatorio.comQuestoes}</Text>
            </View>
            <View style={styles.row}>
              <Text style={[styles.label, { color: theme.danger }]}>✗ Vazios (serão apagados):</Text>
              <Text style={[styles.value, { color: theme.danger }]}>{relatorio.vazios}</Text>
            </View>
          </View>
        )}

        {/* PASSO 2 */}
        {relatorio && relatorio.vazios > 0 && (
          <>
            <Text style={[styles.stepTitle, { color: theme.text, marginTop: 20 }]}>
              Passo 2: Apagar {relatorio.vazios} vazios
            </Text>
            <TouchableOpacity
              style={[styles.btn, { backgroundColor: theme.danger }, limpando && { opacity: 0.6 }]}
              onPress={limpar}
              disabled={limpando}
            >
              {limpando
                ? <ActivityIndicator color="#FFF" />
                : <Text style={styles.btnText}>🗑️ Apagar Simulados Vazios</Text>}
            </TouchableOpacity>
          </>
        )}

        {/* RESULTADO */}
        {resultado && (
          <View style={[styles.resultBox, { backgroundColor: theme.success + '15', borderColor: theme.success }]}>
            <Text style={[styles.resultText, { color: theme.text }]}>{resultado}</Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingTop: 50, paddingBottom: 15, paddingHorizontal: 20, borderBottomWidth: 1,
  },
  iconButton:  { padding: 5 },
  headerTitle: { fontSize: 18, fontWeight: 'bold' },
  scroll:      { padding: 20 },
  warnBox:     { flexDirection: 'row', gap: 12, padding: 16, borderRadius: 12, borderWidth: 1, marginBottom: 24, alignItems: 'center' },
  warnText:    { flex: 1, fontSize: 13, lineHeight: 18 },
  stepTitle:   { fontSize: 16, fontWeight: 'bold', marginBottom: 12 },
  btn:         { paddingVertical: 14, borderRadius: 10, alignItems: 'center' },
  btnText:     { color: '#FFF', fontSize: 16, fontWeight: 'bold' },
  card:        { padding: 16, borderRadius: 12, borderWidth: 1, marginTop: 16 },
  cardTitle:   { fontSize: 15, fontWeight: 'bold', marginBottom: 12 },
  row:         { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  label:       { fontSize: 14 },
  value:       { fontSize: 14, fontWeight: 'bold' },
  resultBox:   { padding: 16, borderRadius: 12, borderWidth: 1, marginTop: 20 },
  resultText:  { fontSize: 14, lineHeight: 20 },
});
