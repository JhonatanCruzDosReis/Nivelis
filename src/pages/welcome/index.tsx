import React, { useState, useEffect } from 'react';
import { View, Text, Image, TouchableOpacity, ScrollView, StatusBar, ActivityIndicator } from 'react-native';
import { style } from './styles';
import { MaterialIcons, FontAwesome5, Ionicons } from '@expo/vector-icons';
import { useNavigation, useIsFocused } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useTheme } from '../TemasAcoes/Temas';

import Logo from '../../assets/NivelisLogo.png'; 

export default function Home() {
    const navigation = useNavigation<any>();
    const isFocused = useIsFocused();
    const { isDarkMode } = useTheme(); 
    
    const [nomeUsuario, setNomeUsuario] = useState('');
    const [avatarUri, setAvatarUri] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true); // NOVO: Estado de carregamento

    const theme = {
        bg: isDarkMode ? "#12121b" : "#F5F5F7",
        text: isDarkMode ? "#FFFFFF" : "#333333",
        card: isDarkMode ? "#1e1e2d" : "#FFFFFF",
        subtext: isDarkMode ? "#CCC" : "#666",
        border: isDarkMode ? "transparent" : "#DDD"
    };

    useEffect(() => {
        const carregarDados = async () => {
            setIsLoading(true); // Inicia o carregamento
            try {
                const savedData = await AsyncStorage.getItem('@user_profile_data');
                if (savedData !== null) {
                    const data = JSON.parse(savedData);
                    setNomeUsuario(data.nome || "Usuário");
                    setAvatarUri(data.avatarUri || null);
                } else {
                    setNomeUsuario("Usuário");
                }
            } catch (error) {
                console.error("Erro ao carregar dados do storage", error);
                setNomeUsuario("Usuário");
            } finally {
                setIsLoading(false); // Finaliza o carregamento
            }
        };

        if (isFocused) {
            carregarDados();
        }
    }, [isFocused]);

    // Tela de carregamento enquanto busca os dados do Login/Cadastro
    if (isLoading) {
        return (
            <View style={[style.container, { backgroundColor: theme.bg, justifyContent: 'center', alignItems: 'center' }]}>
                <ActivityIndicator size="large" color="#7D53DD" />
                <Text style={{ color: theme.subtext, marginTop: 10 }}>Preparando seu ambiente...</Text>
            </View>
        );
    }

    return (
        <ScrollView 
            style={[style.container, { backgroundColor: theme.bg }]} 
            showsVerticalScrollIndicator={false}
        >
            <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />
            
            {/* CABEÇALHO */}
            <View style={style.header}>
                <View>
                    <Text style={[style.greetingText, { color: theme.subtext }]}>Bem-vindo</Text>
                    <Text style={[style.userName, { color: theme.text }]}>{nomeUsuario}</Text>
                </View>
                
                <TouchableOpacity 
                    accessibilityRole="button"
                    accessibilityLabel="Abrir meus dados"
                    style={[style.profileImage, { backgroundColor: theme.card, borderColor: theme.border, borderWidth: isDarkMode ? 0 : 1 }]} 
                    activeOpacity={0.8}
                    onPress={() => navigation.navigate('MeusDados')}
                >
                    {avatarUri ? (
                        <Image 
                            source={{ uri: avatarUri }} 
                            style={{ width: '100%', height: '100%', borderRadius: 25 }} 
                        />
                    ) : (
                        <FontAwesome5 name="user-alt" size={20} color={isDarkMode ? "#ffffff" : "#7D53DD"} />
                    )}
                </TouchableOpacity>
            </View>

            {/* LOGO CENTRAL */}
            <View style={style.logoContainer}>
                <Image 
                    source={Logo} 
                    style={[style.logo, { tintColor: '#7D53DD' }]} 
                    resizeMode="contain" 
                />
            </View>

            {/* MENU DE CARDS */}
            <View style={style.menuContainer}>
                
                {/* CARD CONCURSOS */}
                <TouchableOpacity accessibilityRole="button" 
                    style={[style.card, { backgroundColor: theme.card, borderColor: theme.border, borderWidth: isDarkMode ? 0 : 1 }]} 
                    activeOpacity={0.8}
                    onPress={() => navigation.navigate('Concursos')}
                >
                    <Text style={[style.cardTitle, { color: theme.text }]}>Concursos</Text>
                    <View style={style.cardIconContainer}>
                        <MaterialIcons name="track-changes" size={35} color="#7D53DD" />
                    </View>
                </TouchableOpacity>

                {/* CARD ENADE - O erro estava em cima deste componente! */}
                <TouchableOpacity accessibilityRole="button"
                    onPress={() => navigation.navigate('EnemEnade')} 
                    style={[style.card, { backgroundColor: theme.card, borderColor: theme.border, borderWidth: isDarkMode ? 0 : 1 }]} 
                    activeOpacity={0.8}
                >
                    <Text style={[style.cardTitle, { color: theme.text }]}>Enade / Enem</Text>
                    <View style={style.cardIconContainer}>
                        <FontAwesome5 name="graduation-cap" size={30} color="#7D53DD" />
                    </View>
                </TouchableOpacity>

                {/* CARD QUEM SOMOS */}
                <TouchableOpacity accessibilityRole="button" 
                    style={[style.card, { backgroundColor: theme.card, borderColor: theme.border, borderWidth: isDarkMode ? 0 : 1 }]} 
                    activeOpacity={0.8}
                    onPress={() => navigation.navigate('QuemSomos')}
                >
                    <Text style={[style.cardTitle, { color: theme.text }]}>Quem Somos?</Text>
                    <View style={style.cardIconContainer}>
                        <Ionicons name="help-circle-outline" size={38} color="#7D53DD" />
                    </View>
                </TouchableOpacity>

            </View>
        </ScrollView>
    );
}