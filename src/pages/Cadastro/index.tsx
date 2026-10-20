import React, { useState } from "react";
import {
    View, Text, TextInput, TouchableOpacity,
    ScrollView, KeyboardAvoidingView, Platform,
    Modal, ActivityIndicator, StatusBar
} from "react-native";
import { useTheme } from '../TemasAcoes/Temas';

import {
    MaterialIcons, FontAwesome, Feather, MaterialCommunityIcons
} from '@expo/vector-icons';

import { style } from "./styles";
import AsyncStorage from '@react-native-async-storage/async-storage';

import { auth, db } from '../../services/firebase';
import { createUserWithEmailAndPassword } from "firebase/auth";
import { doc, setDoc } from "firebase/firestore";

import NivelisModal, { useNivelisModal } from '../../components/NivelisModal';

export default function Cadastro({ navigation }: any) {
    const [nome,             setNome]             = useState('');
    const [email,            setEmail]            = useState('');
    const [dataNascimento,   setDataNascimento]   = useState('');
    const [celular,          setCelular]          = useState('');
    const [senha,            setSenha]            = useState('');
    const [confirmarSenha,   setConfirmarSenha]   = useState('');
    const [aceitoTermos,     setAceitoTermos]     = useState(false);
    const [modalVisivel,     setModalVisivel]     = useState(false);
    const [ocultarSenha,     setOcultarSenha]     = useState(true);
    const [ocultarConfirmar, setOcultarConfirmar] = useState(true);
    const [carregando,       setCarregando]       = useState(false);

    const { modal, showModal } = useNivelisModal();
    const { isDarkMode } = useTheme();
    const t = {
        bg:        isDarkMode ? '#000000' : '#F5F5F7',
        card:      isDarkMode ? '#000000' : '#FFFFFF',
        modalCard: isDarkMode ? '#1A1A1A' : '#FFFFFF',
        text:      isDarkMode ? '#FFFFFF' : '#1A1A1A',
        sub:       isDarkMode ? '#8C8C8C' : '#707070',
        border:    isDarkMode ? '#888888' : '#BBBBBB',
        backBg:    isDarkMode ? '#333333' : '#EEEEEE',
        backIcon:  isDarkMode ? '#FFFFFF' : '#333333',
    };

    // ── validações ──────────────────────────────────────────────────────────
    //
    // O validarCPF saiu junto com o campo. O app NUNCA lia o CPF de volta —
    // procurei em todo o src/ e só existia a gravação. Era dado sensível de
    // LGPD coletado sem finalidade nenhuma, e exposto pelas regras do
    // Firestore. A forma mais barata de proteger um dado é não ter o dado.

    const validarIdade = (data: string) => {
        const [dia, mes, ano] = data.split('/').map(Number);
        const nasc  = new Date(ano, mes - 1, dia);
        const hoje  = new Date();
        if (nasc.getDate() !== dia || nasc.getMonth() !== mes - 1 || nasc.getFullYear() !== ano) return false;
        const idade = hoje.getFullYear() - nasc.getFullYear();
        return nasc <= hoje && idade <= 120 && idade >= 0;
    };

    // ── máscaras ─────────────────────────────────────────────────────────────
    const mascaraData = (v: string) =>
        v.replace(/\D/g, "").replace(/(\d{2})(\d)/, "$1/$2").replace(/(\d{2})(\d)/, "$1/$2").substring(0, 10);

    const mascaraCelular = (v: string) =>
        v.replace(/\D/g, "").replace(/(\d{2})(\d)/, "($1) $2").replace(/(\d{5})(\d)/, "$1-$2").substring(0, 15);

    // ── cadastro ─────────────────────────────────────────────────────────────
    const realizarCadastro = async () => {
        const emailLimpo  = email.toLowerCase().trim();
        const celularLimpo = celular.replace(/\D/g, "");

        if (!nome || !emailLimpo || !dataNascimento || !senha) {
            showModal('Atenção', 'Preencha todos os campos obrigatórios.', 'warning');
            return;
        }
        if (!validarIdade(dataNascimento)) {
            showModal('Data inválida', 'A data de nascimento é inválida ou incoerente.', 'error');
            return;
        }
        if (senha !== confirmarSenha) {
            showModal('Senhas diferentes', 'As senhas digitadas não são iguais!', 'error');
            return;
        }
        if (!aceitoTermos) {
            showModal('Termos de uso', 'Você precisa aceitar os termos de uso para continuar.', 'warning');
            return;
        }

        setCarregando(true);

        try {
            const userCredential = await createUserWithEmailAndPassword(auth, emailLimpo, senha);
            const user = userCredential.user;

            const partes      = nome.trim().split(' ');
            const primeiroNome = partes[0];
            const sobrenome   = partes.length > 1 ? partes.slice(1).join(' ') : '';

            await setDoc(doc(db, "users", user.uid), {
                Nome:            primeiroNome,
                Sobrenome:       sobrenome,
                email:           emailLimpo,
                data_nascimento: dataNascimento,
                celular:         celularLimpo,
                Criado_em:       new Date().toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo" }),
            });

            await AsyncStorage.setItem('@usuario_nome', nome);
            await AsyncStorage.setItem('@user_profile_data', JSON.stringify({
                nome,
                email:     emailLimpo,
                dataNasc:  dataNascimento,
                celular,
                avatarUri: null,
            }));

            showModal(
                'Conta criada! 🎉',
                'Seu cadastro foi realizado com sucesso. Faça login para continuar.',
                'success',
                [{ text: 'Ir para Login', onPress: () => navigation.navigate('Login') }],
            );

        } catch (error: any) {
            console.error("Erro no Firebase:", error);

            if (error.code === 'auth/email-already-in-use') {
                showModal('E-mail em uso', 'Este e-mail já está cadastrado em outra conta.', 'warning');
            } else if (error.code === 'auth/weak-password') {
                showModal('Senha fraca', 'A senha deve ter pelo menos 6 caracteres.', 'warning');
            } else if (error.code === 'auth/invalid-email') {
                showModal('E-mail inválido', 'O formato do e-mail é inválido.', 'error');
            } else {
                showModal('Erro', 'Ocorreu um erro ao criar a conta. Tente novamente.', 'error');
            }
        } finally {
            setCarregando(false);
        }
    };

    return (
        <KeyboardAvoidingView
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={{ flex: 1, backgroundColor: t.bg }}
        >
            <StatusBar barStyle={isDarkMode ? 'light-content' : 'dark-content'} backgroundColor={t.bg} />
            <ScrollView style={[style.container, { backgroundColor: t.bg }]} showsVerticalScrollIndicator={false}>

                {/* Modal de Termos */}
                <Modal visible={modalVisivel} animationType="fade" transparent>
                    <View style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center' }}>
                        <View style={{ width: '85%', backgroundColor: t.modalCard, borderRadius: 10, padding: 20 }}>
                            <Text style={{ color: t.text, fontSize: 18, fontWeight: 'bold', marginBottom: 10 }}>Termos de Uso</Text>
                            <ScrollView style={{ maxHeight: 300 }}>
                                <Text style={{ color: t.sub }}>
                                    Bem-vindo ao Nivelis! Ao utilizar nosso aplicativo, você concorda em:{'\n\n'}
                                    • Fornecer informações verídicas no cadastro.{'\n'}
                                    • Usar a plataforma apenas para fins educacionais.{'\n'}
                                    • Não compartilhar sua conta com terceiros.{'\n'}
                                    • Respeitar os direitos autorais dos conteúdos disponibilizados.{'\n\n'}
                                    Seus dados são protegidos conforme a LGPD (Lei 13.709/2018).
                                </Text>
                            </ScrollView>
                            <TouchableOpacity accessibilityRole="button" onPress={() => setModalVisivel(false)} style={[style.button, { marginTop: 15 }]}>
                                <Text style={style.buttonText}>Fechar</Text>
                            </TouchableOpacity>
                        </View>
                    </View>
                </Modal>

                <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} style={[style.backButton, { backgroundColor: t.backBg }]} onPress={() => navigation.goBack()}
                  accessibilityRole="button"
                  accessibilityLabel="Voltar"
                >
                    <MaterialIcons name="arrow-back" size={30} color={t.backIcon} />
                </TouchableOpacity>

                <View style={style.header}>
                    <Text style={[style.title, { color: t.text }]}>Criar conta</Text>
                </View>

                <View style={style.form}>
                    <View style={[style.inputContainer, { borderColor: t.border, backgroundColor: t.card }]}>
                        <TextInput style={[style.input, { color: t.text }]} placeholder="Nome Completo" placeholderTextColor="#666" value={nome} onChangeText={setNome} />
                        <FontAwesome name="user-o" size={18} color="#666" />
                    </View>
                    <View style={[style.inputContainer, { borderColor: t.border, backgroundColor: t.card }]}>
                        <TextInput style={[style.input, { color: t.text }]} placeholder="Email" placeholderTextColor="#666" value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" />
                        <MaterialIcons name="mail-outline" size={18} color="#666" />
                    </View>
                    <View style={[style.inputContainer, { borderColor: t.border, backgroundColor: t.card }]}>
                        <TextInput style={[style.input, { color: t.text }]} placeholder="Data de Nascimento (DD/MM/AAAA)" placeholderTextColor="#666" value={dataNascimento} onChangeText={v => setDataNascimento(mascaraData(v))} keyboardType="numeric" maxLength={10} />
                        <FontAwesome name="calendar-o" size={18} color="#666" />
                    </View>
                    <View style={[style.inputContainer, { borderColor: t.border, backgroundColor: t.card }]}>
                        <TextInput style={[style.input, { color: t.text }]} placeholder="Celular (Opcional)" placeholderTextColor="#666" value={celular} onChangeText={v => setCelular(mascaraCelular(v))} keyboardType="phone-pad" maxLength={15} />
                        <Feather name="phone" size={18} color="#666" />
                    </View>
                    <View style={[style.inputContainer, { borderColor: t.border, backgroundColor: t.card }]}>
                        <TextInput style={[style.input, { color: t.text }]} placeholder="Senha" placeholderTextColor="#666" secureTextEntry={ocultarSenha} value={senha} onChangeText={setSenha} />
                        <TouchableOpacity onPress={() => setOcultarSenha(!ocultarSenha)}
                                              accessibilityRole="button"
                                              accessibilityLabel={ocultarSenha ? "Mostrar a senha" : "Ocultar a senha"}
                                              hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}>
                            <MaterialCommunityIcons name={ocultarSenha ? "eye-off-outline" : "eye-outline"} size={20} color="#666" />
                        </TouchableOpacity>
                    </View>
                    <View style={[style.inputContainer, { borderColor: t.border, backgroundColor: t.card }]}>
                        <TextInput style={[style.input, { color: t.text }]} placeholder="Confirmar Senha" placeholderTextColor="#666" secureTextEntry={ocultarConfirmar} value={confirmarSenha} onChangeText={setConfirmarSenha} />
                        <TouchableOpacity onPress={() => setOcultarConfirmar(!ocultarConfirmar)}
                                              accessibilityRole="button"
                                              accessibilityLabel={ocultarConfirmar ? "Mostrar a confirmação da senha" : "Ocultar a confirmação da senha"}
                                              hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }}>
                            <MaterialCommunityIcons name={ocultarConfirmar ? "eye-off-outline" : "eye-outline"} size={20} color="#666" />
                        </TouchableOpacity>
                    </View>

                    <View style={style.termsContainer}>
                        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} onPress={() => setAceitoTermos(!aceitoTermos)} style={[style.checkbox, { backgroundColor: aceitoTermos ? '#7D53DD' : 'transparent' }]}
                          accessibilityRole="button"
                          accessibilityLabel="Confirmar"
                        >
                            {aceitoTermos && <MaterialIcons name="check" size={14} color="#FFF" />}
                        </TouchableOpacity>
                        <Text style={[style.termsText, { color: t.sub }]}>
                            Li e aceito os{' '}
                            <Text style={{ color: isDarkMode ? '#9775E4' : '#7D53DD', textDecorationLine: 'underline' }}
                                  onPress={() => setModalVisivel(true)}>
                                termos de uso
                            </Text>
                        </Text>
                    </View>
                </View>

                <View style={{ padding: 20, marginBottom: 30 }}>
                    <TouchableOpacity accessibilityRole="button"
                        style={[style.button, carregando && { opacity: 0.7 }]}
                        onPress={realizarCadastro}
                        disabled={carregando}
                    >
                        {carregando
                            ? <ActivityIndicator size="small" color="#FFF" />
                            : <Text style={style.buttonText}>Cadastrar</Text>
                        }
                    </TouchableOpacity>
                </View>
            </ScrollView>

            <NivelisModal {...modal} />
        </KeyboardAvoidingView>
    );
}
