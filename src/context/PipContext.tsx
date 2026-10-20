/**
 * PipContext — player flutuante persistente
 *
 * Renderiza um WebView em miniatura fixado no canto inferior direito da tela,
 * acima de qualquer tela de navegação. Sobrevive ao desmonte do AulaPlayer.
 * Fecha apenas quando o usuário aperta o X.
 */
import React, { createContext, useContext, useState, useCallback } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Dimensions,
} from 'react-native';
import { WebView } from 'react-native-webview';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');
const PIP_W = Math.round(width * 0.50);
const PIP_H = Math.round(PIP_W * 9 / 16) + 32;

export type VideoSource = { html: string; baseUrl: string };

interface PipContextValue {
  startPip: (source: VideoSource, titulo: string) => void;
  stopPip:  () => void;
  isPip:    boolean;
}

const PipContext = createContext<PipContextValue>({
  startPip: () => {},
  stopPip:  () => {},
  isPip:    false,
});

export const usePip = () => useContext(PipContext);

export function PipProvider({ children }: { children: React.ReactNode }) {
  const [source,  setSource]  = useState<VideoSource | null>(null);
  const [titulo,  setTitulo]  = useState('');
  const [visible, setVisible] = useState(false);

  const startPip = useCallback((src: VideoSource, t: string) => {
    setSource(src);
    setTitulo(t);
    setVisible(true);
  }, []);

  const stopPip = useCallback(() => {
    setVisible(false);
    // Adia o destroy do source para a animação não cortar o vídeo
    setTimeout(() => setSource(null), 400);
  }, []);

  return (
    <PipContext.Provider value={{ startPip, stopPip, isPip: visible }}>
      {/* flex:1 para o conteúdo ocupar a tela toda */}
      <View style={{ flex: 1 }}>
        {children}

        {/* Janela PiP — flutua acima de tudo via position absolute */}
        {visible && source && (
          <View style={styles.window}>
            {/* Barra superior */}
            <View style={styles.bar}>
              <Text style={styles.barTitle} numberOfLines={1}>{titulo}</Text>
              <TouchableOpacity
                onPress={stopPip}
                hitSlop={{ top: 10, right: 10, bottom: 10, left: 10 }}
                accessibilityRole="button"
                accessibilityLabel="Fechar"
              >
                <Ionicons name="close-circle" size={20} color="#FFF" />
              </TouchableOpacity>
            </View>

            {/* Player */}
            <WebView
              source={source}
              incognito
              style={{ flex: 1, backgroundColor: '#000' }}
              allowsFullscreenVideo
              allowsInlineMediaPlayback
              allowsPictureInPictureMediaPlayback
              mediaPlaybackRequiresUserAction={false}
              javaScriptEnabled
              domStorageEnabled
              originWhitelist={['*']}
              mixedContentMode="always"
            />
          </View>
        )}
      </View>
    </PipContext.Provider>
  );
}

const styles = StyleSheet.create({
  window: {
    position: 'absolute',
    bottom: 88,      // Acima da tab bar
    right: 14,
    width: PIP_W,
    height: PIP_H,
    borderRadius: 10,
    overflow: 'hidden',
    backgroundColor: '#111',
    // Sombra (iOS)
    shadowColor: '#000',
    shadowOpacity: 0.65,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 4 },
    // Elevação (Android)
    elevation: 30,
    zIndex: 9999,
  },
  bar: {
    height: 32,
    backgroundColor: '#000',
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    gap: 8,
  },
  barTitle: { flex: 1, color: '#FFF', fontSize: 11, fontWeight: '600' },
});
