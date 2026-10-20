import React from 'react';
import {
  Modal, View, Text, TouchableOpacity, StyleSheet, Dimensions
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../pages/TemasAcoes/Temas';

const { width } = Dimensions.get('window');

export type ModalType = 'info' | 'success' | 'error' | 'producao' | 'warning';

export interface ModalButton {
  text: string;
  onPress: () => void;
  style?: 'primary' | 'secondary' | 'danger';
}

export interface NivelisModalProps {
  visible: boolean;
  title: string;
  message: string;
  buttons: ModalButton[];
  type?: ModalType;
  onClose?: () => void;
}

const ICON_MAP: Record<ModalType, { name: string; color: string }> = {
  info:     { name: 'information-circle-outline', color: '#7D53DD' },
  success:  { name: 'check-circle-outline',       color: '#10B981' },
  error:    { name: 'close-circle-outline',        color: '#EF4444' },
  warning:  { name: 'alert-circle-outline',        color: '#F59E0B' },
  producao: { name: 'wrench-clock',                color: '#F59E0B' },
};

export default function NivelisModal({
  visible,
  title,
  message,
  buttons,
  type = 'info',
  onClose,
}: NivelisModalProps) {
  const { isDarkMode } = useTheme();

  const theme = {
    bg:      isDarkMode ? '#1A1A2E' : '#FFFFFF',
    text:    isDarkMode ? '#FFFFFF' : '#1A1A1A',
    sub:     isDarkMode ? '#AAA'    : '#666666',
    border:  isDarkMode ? '#2E2E4E' : '#E5E5E5',
    overlay: 'rgba(0,0,0,0.80)',
    accent:  '#7D53DD',
  };

  const { name, color } = ICON_MAP[type];

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      statusBarTranslucent
      onRequestClose={() => onClose?.()}
    >
      <View style={[styles.overlay, { backgroundColor: theme.overlay }]}>
        <View style={[styles.card, { backgroundColor: theme.bg, borderColor: theme.border }]}>

          {/* Ícone */}
          <View style={[styles.iconCircle, { backgroundColor: color + '18' }]}>
            <MaterialCommunityIcons name={name as any} size={40} color={color} />
          </View>

          {/* Textos */}
          <Text style={[styles.title, { color: theme.text }]}>{title}</Text>
          <Text style={[styles.message, { color: theme.sub }]}>{message}</Text>

          {/* Divisor */}
          <View style={[styles.divider, { backgroundColor: theme.border }]} />

          {/* Botões */}
          <View style={[styles.buttonRow, buttons.length === 1 && styles.buttonSingle]}>
            {buttons.map((btn, i) => {
              const isPrimary   = !btn.style || btn.style === 'primary';
              const isSecondary = btn.style === 'secondary';
              const isDanger    = btn.style === 'danger';

              return (
                <TouchableOpacity
                  key={i}
                  onPress={() => { btn.onPress(); onClose?.(); }}
                  activeOpacity={0.8}
                  style={[
                    styles.button,
                    buttons.length > 1 && styles.buttonFlex,
                    isPrimary   && { backgroundColor: theme.accent },
                    isSecondary && { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: theme.accent },
                    isDanger    && { backgroundColor: '#EF4444' },
                  ]}
                >
                  <Text style={[
                    styles.buttonText,
                    isSecondary && { color: theme.accent },
                  ]}>
                    {btn.text}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>
      </View>
    </Modal>
  );
}

// ─── hook helper ───────────────────────────────────────────────────────────────
// Uso: const { modal, showModal, closeModal } = useNivelisModal();
// Depois adicione <NivelisModal {...modal} /> no return e chame showModal(...)
export function useNivelisModal() {
  const [modal, setModal] = React.useState<NivelisModalProps>({
    visible: false,
    title: '',
    message: '',
    buttons: [],
    type: 'info',
  });

  const closeModal = React.useCallback(() =>
    setModal(m => ({ ...m, visible: false })), []);

  const showModal = React.useCallback((
    title: string,
    message: string,
    type: ModalType = 'info',
    buttons?: ModalButton[],
  ) => {
    setModal(m => ({
      ...m,
      visible: true,
      title,
      message,
      type,
      onClose: () => setModal(prev => ({ ...prev, visible: false })),
      buttons: buttons ?? [{ text: 'OK', onPress: () => {} }],
    }));
  }, []);

  return { modal, showModal, closeModal };
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  card: {
    width: '100%',
    maxWidth: 400,
    borderRadius: 24,
    padding: 28,
    alignItems: 'center',
    borderWidth: 1,
    elevation: 20,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 10 },
  },
  iconCircle: {
    width: 76,
    height: 76,
    borderRadius: 38,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
  },
  message: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 22,
  },
  divider: {
    width: '100%',
    height: 1,
    marginVertical: 22,
  },
  buttonRow: {
    flexDirection: 'row',
    gap: 10,
    width: '100%',
  },
  buttonSingle: {
    justifyContent: 'center',
  },
  buttonFlex: {
    flex: 1,
  },
  button: {
    paddingVertical: 14,
    borderRadius: 14,
    alignItems: 'center',
    minWidth: 80,
  },
  buttonText: {
    color: '#FFF',
    fontSize: 15,
    fontWeight: 'bold',
  },
});
