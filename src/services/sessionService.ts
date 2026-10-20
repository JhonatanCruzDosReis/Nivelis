// Sessão persistente com expiração de 7 dias
// Fluxo: login → save() renova o timer
//        startup → check() valida; se expirado faz signOut automático

import AsyncStorage from '@react-native-async-storage/async-storage';
import { signOut } from 'firebase/auth';
import { auth } from './firebase';

const SESSION_KEY  = '@nivelis_session';
const EXPIRY_7DAYS = 7 * 24 * 60 * 60 * 1000; // 7 dias em ms

interface SessionData {
  uid:       string;
  lastLogin: number; // Date.now() no momento do login
}

export const sessionService = {

  /**
   * Salva/renova a sessão. Deve ser chamado SEMPRE após login bem-sucedido.
   * Reinicia o contador de 7 dias.
   */
  save: async (uid: string): Promise<void> => {
    const data: SessionData = { uid, lastLogin: Date.now() };
    await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(data));
  },

  /**
   * Verifica se a sessão existe e está dentro dos 7 dias.
   * Se estiver expirada, faz signOut do Firebase e remove o token.
   * @returns true se a sessão é válida, false se expirada/inexistente.
   */
  check: async (): Promise<boolean> => {
    try {
      const raw = await AsyncStorage.getItem(SESSION_KEY);
      if (!raw) return false;

      const { lastLogin } = JSON.parse(raw) as SessionData;
      const elapsed = Date.now() - lastLogin;

      if (elapsed > EXPIRY_7DAYS) {
        // Token expirou — limpar tudo
        await sessionService.clear();
        return false;
      }

      return true;
    } catch {
      return false;
    }
  },

  /**
   * Remove o token e faz logout do Firebase.
   * Usar no botão "Sair" e quando a sessão expira.
   */
  clear: async (): Promise<void> => {
    await AsyncStorage.removeItem(SESSION_KEY).catch(() => {});
    await signOut(auth).catch(() => {});
  },

  /**
   * Quantos dias restam até o token expirar.
   * 0 = expirado ou inexistente.
   */
  diasRestantes: async (): Promise<number> => {
    try {
      const raw = await AsyncStorage.getItem(SESSION_KEY);
      if (!raw) return 0;
      const { lastLogin } = JSON.parse(raw) as SessionData;
      const restante = EXPIRY_7DAYS - (Date.now() - lastLogin);
      return Math.max(0, Math.floor(restante / (24 * 60 * 60 * 1000)));
    } catch {
      return 0;
    }
  },
};
