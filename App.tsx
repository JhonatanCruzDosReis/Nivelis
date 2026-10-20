import 'react-native-gesture-handler';
import React, { useEffect } from 'react';
import { StatusBar as RNStatusBar, Platform } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import Routes from './src/routes';
import { StatusBar } from 'expo-status-bar';
import { setupDatabase } from './src/services/database';
import { pingApi } from './src/services/apiService';
import { ThemeProvider, useTheme } from './src/pages/TemasAcoes/Temas';
import { PipProvider } from './src/context/PipContext';
import * as NavigationBar from 'expo-navigation-bar';

function AppStatusBar() {
  const { isDarkMode } = useTheme();
  return <StatusBar hidden={true} style={isDarkMode ? "light" : "dark"} />;
}

export default function App() {
  useEffect(() => {
    let timeoutId: any;
    let listener: { remove: () => void } | null = null;

    const ocultarBarra = async () => {
      // NavigationBar so existe no Android — pula no web/iOS
      if (Platform.OS !== 'android') return;
      try {
        await NavigationBar.setVisibilityAsync("hidden");
        await NavigationBar.setBehaviorAsync("overlay-swipe");
        RNStatusBar.setHidden(true);
      } catch (e) {
        console.log("Erro ao ocultar barra inferior:", e);
      }
    };

    ocultarBarra();

    // addVisibilityListener tambem so existe no Android
    if (Platform.OS === 'android') {
      listener = NavigationBar.addVisibilityListener(({ visibility }) => {
        if (visibility === 'visible') {
          clearTimeout(timeoutId);
          timeoutId = setTimeout(() => {
            ocultarBarra();
          }, 3000);
        }
      });
    }

    setupDatabase();
    pingApi().catch(() => {});

    return () => {
      listener?.remove();
      clearTimeout(timeoutId);
    };
  }, []);

  return (
    <ThemeProvider>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <PipProvider>
          <NavigationContainer>
            <Routes />
            <AppStatusBar />
          </NavigationContainer>
        </PipProvider>
      </GestureHandlerRootView>
    </ThemeProvider>
  );
}