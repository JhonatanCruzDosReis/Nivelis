import React, { useState } from "react";
import {
    Text, View, Image, TextInput,
    TouchableOpacity, ActivityIndicator, StatusBar
} from 'react-native';
import { useTheme } from '../TemasAcoes/Temas';

import { style } from "./styles";
import Logo from '../../assets/NivelisLogo.png';
import { MaterialIcons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { auth, db } from '../../services/firebase';
import { signInWithEmailAndPassword } from "firebase/auth";
import { doc, getDoc } from "firebase/firestore";
import { sessionService } from '../../services/sessionService';

import NivelisModal, { useNivelisModal } from '../../components/NivelisModal';

export default function Login({ navigation }: any) {
    const [email,        setEmail]        = useState('');
    const [senha,        setSenha]        = useState('');
    const [mostrarSenha, setMostrarSenha] = useState(false);
    const [carregando,   setCarregando]   = useState(false);

    const { modal, showModal } = useNivelisModal();
    const { isDarkMode } = useTheme();
    const t = {
        bg:     isDarkMode ? '#000000' : '#F5F5F7',
        card:   isDarkMode ? '#000000' : '#FFFFFF',
        text:   isDarkMode ? '#FFFFFF' : '#1A1A1A',
        label:  isDarkMode ? '#fdfdfddc' : '#444444',
        border: isDarkMode ? '#888888'  : '#BBBBBB',
        sub:    isDarkMode ? '#858585'  : '#707070',   // 2.82/4.11 → 4.6+
    };

    const handleLogin = async () => {
        const emailLimpo = email.toLowerCase().trim();

        if (!emailLimpo || !senha) {
            showModal('Atencao', 'Por favor, preencha todos os campos!', 'warning');
            return;
        }

        setCarregando(true);

        try {
            const userCredential = await signInWithEmailAndPassword(auth, emailLimpo, senha);
            const user = userCredential.user;

            // Renovar/criar token de sessao de 7 dias
            await sessionService.save(user.uid);

            const docRef  = doc(db, "users", user.uid);
            const docSnap = await getDoc(docRef);

            if (docSnap.exists()) {
                const dadosUsuario = docSnap.data();
                await AsyncStorage.setItem('@usuario_nome', dadosUsuario.Nome || dadosUsuario.nome || 'Estudante');
                await AsyncStorage.setItem('@user_profile_data', JSON.stringify({
                    nome:      dadosUsuario.Nome || dadosUsuario.nome || '',
                    email:     dadosUsuario.email || emailLimpo,
                    dataNasc:  dadosUsuario.data_nascimento || '',
                    celular:   dadosUsuario.celular || '',
                    avatarUri: null,
                }));
            } else {
                await AsyncStorage.setItem('@usuario_nome', 'Estudante');
            }

            navigation.navigate('welcome');

        } catch (error: any) {
            console.error("Erro no Login:", error);

            if (['auth/invalid-credential', 'auth/wrong-password', 'auth/user-not-found'].includes(error.code)) {
                showModal('Erro de Login', 'E-mail ou senha incorretos.', 'error');
            } else if (error.code === 'auth/invalid-email') {
                showModal('Erro', 'O formato do e-mail e invalido.', 'error');
            } else if (error.code === 'auth/network-request-failed') {
                showModal('Sem Conexao', 'Verifique sua internet e tente novamente.', 'warning');
            } else {
                showModal('Erro', 'Ocorreu um erro inesperado. Tente novamente.', 'error');
            }
        } finally {
            setCarregando(false);
        }
    };

    return (
        <View style={[style.container, { backgroundColor: t.bg }]}>
            <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} backgroundColor={t.bg} />

            {/* CAIXA SUPERIOR */}
            <View style={style.boxTop}>
                <Image source={Logo} style={style.logo} resizeMode="contain" />
            </View>

            {/* CAIXA CENTRAL */}
            <View style={style.boxMid}>
                <Text style={[style.tittleInput, { color: t.label }]}>ENDERECO DE E-MAIL</Text>
                <View style={[style.BoxInput, { backgroundColor: t.card, borderColor: t.border }]}>
                    <TextInput
                        style={[style.input, { color: t.text }]}
                        placeholder="exemplo@email.com"
                        placeholderTextColor="#808080"
                        value={email}
                        onChangeText={setEmail}
                        autoCapitalize="none"
                        keyboardType="email-address"
                    />
                    <MaterialIcons name='email' size={20} color={'#888'} />
                </View>

                <Text style={[style.tittleInput, { color: t.label }]}>SENHA</Text>
                <View style={[style.BoxInput, { backgroundColor: t.card, borderColor: t.border }]}>
                    <TextInput
                        style={[style.input, { color: t.text }]}
                        secureTextEntry={!mostrarSenha}
                        placeholder="********"
                        placeholderTextColor="#808080"
                        value={senha}
                        onChangeText={setSenha}
                    />
                    <TouchableOpacity onPress={() => setMostrarSenha(!mostrarSenha)}
                                        accessibilityRole="button"
                                        accessibilityLabel={mostrarSenha ? "Ocultar a senha" : "Mostrar a senha"}
                                        hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}>
                        <MaterialIcons
                            name={mostrarSenha ? 'visibility-off' : 'remove-red-eye'}
                            size={20}
                            color={'#888'}
                        />
                    </TouchableOpacity>
                </View>
            </View>

            {/* CAIXA INFERIOR */}
            <View style={style.boxBottom}>
                <TouchableOpacity accessibilityRole="button"
                    style={[style.button, carregando && { opacity: 0.7 }]}
                    onPress={handleLogin}
                    disabled={carregando}
                >
                    {carregando ? (
                        <ActivityIndicator size="small" color="#FFF" />
                    ) : (
                        <Text style={style.textButton}>Entrar</Text>
                    )}
                </TouchableOpacity>

                <Text style={[style.textBottom, { color: t.sub }]}>
                    Nao tem conta?
                    <Text style={[style.textBottomBold, { color: isDarkMode ? '#9775E4' : '#7D53DD' }]}
                          onPress={() => navigation.navigate('Cadastro')}>
                        {" "}Crie agora!
                    </Text>
                </Text>
            </View>

            <NivelisModal {...modal} />
        </View>
    );
}
