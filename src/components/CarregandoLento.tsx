// ─────────────────────────────────────────────────────────────────────────────
//  CARREGANDO LENTO — a espera que não parece travamento
//
//  A API vive no plano gratuito do Render, que HIBERNA quando ninguém usa: a
//  primeira chamada depois da soneca leva 30 a 50 segundos, e a cascata de
//  tentativas do app soma timeouts de 60s + 60s + 90s. Antes deste componente
//  o usuário via "Carregando simulado..." numa tela cheia, sem header e sem
//  botão nenhum. Dois minutos assim e qualquer pessoa conclui que travou e
//  mata o aplicativo.
//
//  Três coisas resolvem isso, e nenhuma é técnica:
//    1. dizer a verdade — "o servidor hiberna" é informação que o usuário
//       entende e que transforma espera em expectativa;
//    2. mostrar que o tempo está passando — a mensagem muda aos 15s e aos
//       40s, então a tela prova que está viva;
//    3. deixar sair — um Cancelar visível desde o primeiro segundo.
//
//  O cronômetro é de 1s e só mexe num contador. Nenhum efeito colateral
//  dentro do updater: foi exatamente esse bug que congelou as respostas do
//  simulado quando o tempo zerava.
// ─────────────────────────────────────────────────────────────────────────────

import React, { useEffect, useState } from 'react';
import { View, Text, ActivityIndicator, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export interface CarregandoLentoProps {
  /** O que está sendo montado, na voz do usuário. Ex.: "Montando seu caderno" */
  titulo: string;
  /** Sem isto não há saída da tela. Passe sempre. */
  onCancelar?: () => void;
  tema: {
    bg: string; text: string; sub: string; primary: string;
    border: string; card: string;
  };
  /** Texto do botão de saída. */
  rotuloCancelar?: string;
}

export default function CarregandoLento({
  titulo,
  onCancelar,
  tema,
  rotuloCancelar = 'Cancelar',
}: CarregandoLentoProps) {
  const [segundos, setSegundos] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setSegundos(s => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // A explicação só aparece depois de 3s: numa resposta rápida ela seria
  // ruído, e falar de hibernação quando nada demorou assusta sem motivo.
  const mostrarExplicacao = segundos >= 3;

  const recado =
    segundos >= 40
      ? 'Ainda tentando. Se não vier em alguns segundos, tente de novo mais tarde.'
      : segundos >= 15
        ? 'Ainda tentando — o servidor está acordando.'
        : 'O servidor hiberna quando ninguém usa, então a primeira vez leva '
          + 'de 30 a 50 segundos.';

  return (
    <View style={[estilos.caixa, { backgroundColor: tema.bg }]}>
      <ActivityIndicator size="large" color={tema.primary} />

      <Text style={[estilos.titulo, { color: tema.text }]}>{titulo}</Text>

      {mostrarExplicacao && (
        <Text style={[estilos.recado, { color: tema.sub }]}>{recado}</Text>
      )}

      {mostrarExplicacao && (
        <Text style={[estilos.relogio, { color: tema.sub }]}>
          {segundos}s
        </Text>
      )}

      {onCancelar && (
        <TouchableOpacity
          style={[estilos.btn, { borderColor: tema.border, backgroundColor: tema.card }]}
          onPress={onCancelar}
          accessibilityRole="button"
          accessibilityLabel={rotuloCancelar}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <MaterialCommunityIcons name="close" size={17} color={tema.sub} />
          <Text style={[estilos.btnTxt, { color: tema.sub }]}>{rotuloCancelar}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const estilos = StyleSheet.create({
  caixa: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 32,
  },
  titulo: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 20,
    textAlign: 'center',
  },
  recado: {
    fontSize: 13.5,
    lineHeight: 19,
    textAlign: 'center',
    marginTop: 10,
    maxWidth: 320,
  },
  relogio: {
    fontSize: 12,
    marginTop: 12,
    fontVariant: ['tabular-nums'],
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 26,
    paddingVertical: 11,
    paddingHorizontal: 22,
    borderRadius: 10,
    borderWidth: 1,
  },
  btnTxt: { fontSize: 14, fontWeight: '600' },
});
