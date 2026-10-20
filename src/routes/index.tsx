import React, { useEffect, useState } from 'react';
import { View, ActivityIndicator } from 'react-native';
import { createStackNavigator } from '@react-navigation/stack';
import { onAuthStateChanged } from 'firebase/auth';

import Login              from '../pages/login';
import Cadastro           from '../pages/Cadastro';
import Welcome            from '../pages/welcome';
import QuemSomos          from '../pages/QuemSomos';
import MeusDados          from '../pages/MeusDados';
import HomeEnemEnade      from '../pages/enade';
import MateriasScreen     from '../pages/enade/card_enade/materia';
import AulaPlayer         from '../pages/enade/card_enade/materia/AulaPlayer';
import SimuladosDashboard from '../pages/enade/card_enade/simulados/index';
import SimuladoAndamento  from '../pages/enade/card_enade/simulados/simulados';
import GabaritoScreen     from '../pages/enade/card_enade/simulados/GabaritoScreen';
import QuestoesScreen     from '../pages/enade/card_enade/Questoes/questoes';
import MinhasQuestoes     from '../pages/enade/card_enade/MinhasQuestoes';
import MontarSimulado     from '../pages/enade/card_enade/MontarSimulado';
import Concurso           from '../pages/Concurso';
import LivrosEnade        from '../pages/enade/card_enade/livro';
import Cronograma         from '../pages/enade/card_enade/cronograma/index';

import { auth }           from '../services/firebase';
import { sessionService } from '../services/sessionService';

const Stack = createStackNavigator();

export default function Routes() {
  // null = ainda verificando; depois define 'Login' ou 'welcome'
  const [rotaInicial, setRotaInicial] = useState<'Login' | 'welcome' | null>(null);

  useEffect(() => {
    // onAuthStateChanged espera o Firebase restaurar a sessao persistida do AsyncStorage
    const unsubscribe = onAuthStateChanged(auth, async (usuario) => {
      unsubscribe(); // dispara apenas uma vez na inicializacao

      if (!usuario) {
        // Firebase nao tem usuario logado -> Login
        await sessionService.clear().catch(() => {});
        setRotaInicial('Login');
        return;
      }

      // Firebase tem usuario -> verificar token de 7 dias
      const sessaoValida = await sessionService.check();
      if (!sessaoValida) {
        // Expirou: sessionService.check() ja chamou signOut internamente
        setRotaInicial('Login');
      } else {
        // Tudo OK -> pular login direto para o app
        setRotaInicial('welcome');
      }
    });
  }, []);

  // Splash de carregamento enquanto verifica sessao
  if (rotaInicial === null) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#1A1A2E' }}>
        <ActivityIndicator size="large" color="#E94560" />
      </View>
    );
  }

  return (
    <Stack.Navigator initialRouteName={rotaInicial} screenOptions={{ headerShown: false }}>
      {/* Autenticacao */}
      <Stack.Screen name="Login"    component={Login} />
      <Stack.Screen name="Cadastro" component={Cadastro} />

      {/* Telas principais */}
      <Stack.Screen name="welcome"   component={Welcome} />
      <Stack.Screen name="EnemEnade" component={HomeEnemEnade} />
      <Stack.Screen name="MeusDados" component={MeusDados} />
      <Stack.Screen name="QuemSomos" component={QuemSomos} />
      <Stack.Screen name="Concursos" component={Concurso} />

      {/* Cronograma */}
      <Stack.Screen name="Cronograma" component={Cronograma} />

      {/* Materias e Aulas */}
      <Stack.Screen name="materia"    component={MateriasScreen} />
      <Stack.Screen name="AulaPlayer" component={AulaPlayer} />

      {/* Simulados */}
      <Stack.Screen name="SimuladosDashboard" component={SimuladosDashboard} />
      <Stack.Screen name="SimuladoAndamento"  component={SimuladoAndamento} />
      <Stack.Screen name="GabaritoScreen"     component={GabaritoScreen} />
      <Stack.Screen name="Questoes"           component={QuestoesScreen} />
      <Stack.Screen name="MinhasQuestoes"     component={MinhasQuestoes} />
      <Stack.Screen name="MontarSimulado"     component={MontarSimulado} />

      {/* Livros */}
      <Stack.Screen name="LivrosEnade" component={LivrosEnade} />
    </Stack.Navigator>
  );
}