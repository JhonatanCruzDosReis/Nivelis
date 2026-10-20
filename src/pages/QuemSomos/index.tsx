import React, { useState } from 'react'; 
import { 
  View, Text, Image, TouchableOpacity, 
  ScrollView, StatusBar, Modal, Linking, 
} from 'react-native'; 
import { MaterialIcons, FontAwesome5, Ionicons } from '@expo/vector-icons'; 
import { useNavigation } from '@react-navigation/native';

// ---------------------------------------------------------
// 1. IMPORTAÇÃO DE ESTILOS, TEMA E ASSETS
// ---------------------------------------------------------
import { style } from './styles';
import { useTheme } from '../TemasAcoes/Temas';

import FotoVinicius from '../../assets/VINICIUS.png';
import FotoRenan from '../../assets/RENAN.png';
import FotoCarlos from '../../assets/CARLOS.png';
import FotoNicolas from '../../assets/NICOLAS.png';
import FotoJhonatan from '../../assets/JHONATAN.png';
import FotoGabriel from '../../assets/GABRIEL.png';
import FotoJoao from '../../assets/JOAO.png';

export default function AboutUs() {
    // ---------------------------------------------------------
    // 2. HOOKS E ESTADOS
    // ---------------------------------------------------------
    const navigation = useNavigation<any>();
    const { isDarkMode } = useTheme(); 

    const [selectedMember, setSelectedMember] = useState<any>(null);

    const theme = {
        bg: isDarkMode ? "#12121b" : "#F5F5F7",
        card: isDarkMode ? "#1e1e2d" : "#FFFFFF",
        modalCardBg: isDarkMode ? "#1e1e2d" : "#FFFFFF",
        modalInfoBg: isDarkMode ? "#2a2a3d" : "#f9f9f9",
        text: isDarkMode ? "#FFFFFF" : "#1a1a1a",
        subtext: isDarkMode ? "#CCCCCC" : "#666666",
        iconBg: isDarkMode ? "#202024" : "#E0E0E0",
        overlay: isDarkMode ? 'rgba(0,0,0,0.85)' : 'rgba(0,0,0,0.78)'
    };

    // ---------------------------------------------------------
    // 3. BASE DE DADOS DO TIME
    // ---------------------------------------------------------
    const team = [
        { id: 1, name: 'Vinicius', role: 'Professor / Orientador', type: 'main', image: FotoVinicius, faculdade: 'UNISUAM - CG', turno: 'Integral', modulo: 'N/A', Turma: 'N/A', linkedin: 'https://linkedin.com', contato: 'vinicius@email.com' },
        { id: 2, name: 'Renan Teixeira', role: 'FRONT-END', type: 'small', image: FotoRenan, faculdade: 'UNISUAM - CG ', turno: 'Noite', modulo: 'Desenvolvimento Móbile', Turma: '3º Período', linkedin: 'https://www.linkedin.com/in/renan-teixeira-91944a375/', contato: 'renanteixeira.dev@email.com' },
        { id: 3, name: 'Carlos Eduardo', role: 'FRONT-END', type: 'small', image: FotoCarlos, faculdade: 'UNISUAM - CG', turno: 'Noite', modulo: 'Desenvolvimento Móbile', Turma: '3º Período', linkedin: 'https://linkedin.com', contato: 'vclaudinogomes@gmail.com'},
        { id: 4, name: 'Nicolas Henrique', role: 'BACK-END', type: 'small', image: FotoNicolas, faculdade: 'UNISUAM - CG', turno: 'Noite', modulo: 'Desenvolvimento Móbile', Turma: '3º Período', linkedin: 'https://www.linkedin.com/in/nicolas-henrique-164503353/', contato: 'dormirok@gmail.com' },
        { id: 5, name: 'Jhonatan Cruz', role: 'BACK-END', type: 'small', image: FotoJhonatan, faculdade: 'UNISUAM - CG', turno: 'Noite', modulo: 'Desenvolvimento Móbile', Turma: '3º Período', linkedin: 'https://linkedin.com', contato: 'jhonatan@email.com' },
        { id: 6, name: 'Gabriel Carneiro', role: 'DATA DEVELOPER', type: 'small', image: FotoGabriel, faculdade: 'UNISUAM - CG', turno: 'Noite', modulo: 'Desenvolvimento Móbile', Turma: ' Desenvolvimento Móbile', linkedin: 'https://linkedin.com', contato: 'gabriel@email.com' },
        { id: 7, name: 'João Pedro', role: 'DATA DEVELOPER', type: 'small', image: FotoJoao, faculdade: 'UNISUAM - CG', turno: 'Noite', modulo: 'Desenvolvimento Móbile', Turma: '3º Período', linkedin: 'https://linkedin.com', contato: 'joao@email.com' },
    ];

    return (
        <ScrollView 
            style={[style.container, { backgroundColor: theme.bg }]} 
            contentContainerStyle={style.scrollContent} 
            showsVerticalScrollIndicator={false}
        >
            <StatusBar barStyle={isDarkMode ? "light-content" : "dark-content"} />

            {/* --- CABEÇALHO --- */}
            <View style={style.header}>
                <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} 
                    onPress={() => navigation.goBack()} 
                    style={[style.iconButton, { backgroundColor: theme.iconBg }]}
                  accessibilityRole="button"
                  accessibilityLabel="Voltar"
                >
                    <Ionicons name="arrow-back" size={24} color={theme.text} />
                </TouchableOpacity>
                <Text style={[style.headerTitle, { color: theme.text }]}>Quem Somos</Text>
            </View>

            {/* --- SEÇÃO MISSÃO --- */}
            <View style={style.tagMission}>
                <Text style={style.tagText}>MISSÃO</Text>
            </View>

            <Text style={[style.title, { color: theme.text }]}>
                Arquitetos da {'\n'}
                <Text style={style.titleHighlight}>Educação.</Text>
            </Text>

            <Text style={[style.description, { color: theme.subtext }]}>
                Somos uma equipe dedicada ao desenvolvimento de soluções educacionais inovadoras, focadas em facilitar o acesso ao conhecimento.
            </Text>

            {/* --- LISTAGEM DO TIME --- */}
            <View style={style.sectionHeader}>
                <Text style={[style.sectionTitle, { color: theme.text }]}>Nosso Time</Text>
                <Text style={[style.memberCount, { color: theme.subtext }]}>{team.length} DESENVOLVEDORES</Text>
            </View>

            <View style={style.teamContainer}>
                {team.map((member) => (
                    <TouchableOpacity accessibilityRole="button" 
                        key={member.id} 
                        onPress={() => setSelectedMember(member)}
                        activeOpacity={0.8}
                        style={[
                            member.type === 'main' ? { width: '100%' } : { width: '48%' },
                            { position: 'relative' }
                        ]}
                    >
                        {member.type === 'main' ? (
                            <View style={[style.mainCard, { backgroundColor: theme.overlay }]}>
                                <Image source={member.image} style={style.avatarCircle} />
                                <View style={style.cardInfo}>
                                    <Text style={[style.memberNameLarge, { color: '#FFF' }]}>{member.name}</Text>
                                    <Text style={style.memberRoleHighlight}>{member.role}</Text>
                                </View>
                                <MaterialIcons name="add-circle-outline" size={20} color="#ffffff" style={{ position: 'absolute', right: 15, top: 15 }} />
                            </View>
                        ) : (
                            <View style={[style.smallCard, { backgroundColor: theme.overlay }]}>
                                <Image source={member.image} style={style.avatarSmall} />
                                <Text style={[style.memberNameSmall, { color: '#FFF' }]}>{member.name}</Text>
                                <Text style={[style.memberRoleSmall, { color: '#CCC' }]}>{member.role}</Text>
                                <MaterialIcons name="add-circle-outline" size={14} color="#ffffff" style={{ position: 'absolute', right: 8, bottom: 8, opacity: 0.6 }} />
                            </View>
                        )}
                    </TouchableOpacity>
                ))}
            </View>

            {/* --- MODAL DE DETALHES --- */}
            <Modal
                visible={!!selectedMember}
                transparent={true}
                animationType="fade"
                onRequestClose={() => setSelectedMember(null)}
            >
                <View style={{ flex: 1, backgroundColor: theme.overlay, justifyContent: 'center', alignItems: 'center', padding: 20 }}>
                    <View style={{ backgroundColor: theme.modalCardBg, width: '100%', borderRadius: 20, padding: 20, alignItems: 'center' }}>
                        
                        <TouchableOpacity hitSlop={{ top: 16, bottom: 16, left: 16, right: 16 }} 
                            style={{ alignSelf: 'flex-end', padding: 5 }} 
                            onPress={() => setSelectedMember(null)}
                          accessibilityRole="button"
                          accessibilityLabel="Fechar"
                        >
                            <MaterialIcons name="close" size={28} color={theme.text} />
                        </TouchableOpacity>

                        {selectedMember?.image && (
                            <Image 
                                source={selectedMember.image} 
                                style={{ width: 100, height: 100, borderRadius: 50, marginBottom: 15 }} 
                            />
                        )}

                        <Text style={{ fontSize: 22, fontWeight: 'bold', color: theme.text }}>{selectedMember?.name}</Text>
                        <Text style={{ fontSize: 16, color: '#7c29e5', marginBottom: 20, fontWeight: '600' }}>{selectedMember?.role}</Text>

                        <View style={{ width: '100%', backgroundColor: theme.modalInfoBg, borderRadius: 12, padding: 15, marginBottom: 20 }}>
                            <Text style={{ marginBottom: 5, color: theme.text }}>
                                <Text style={{ fontWeight: 'bold' }}>Faculdade:</Text> {selectedMember?.faculdade}
                            </Text>
                            <Text style={{ marginBottom: 5, color: theme.text }}>
                                <Text style={{ fontWeight: 'bold' }}>Turno:</Text> {selectedMember?.turno}
                            </Text>
                            <Text style={{ marginBottom: 5, color: theme.text }}>
                                <Text style={{ fontWeight: 'bold' }}>Módulo:</Text> {selectedMember?.modulo}
                            </Text>
                            <Text style={{ marginBottom: 5, color: theme.text }}>
                                <Text style={{ fontWeight: 'bold' }}>Turma:</Text> {selectedMember?.Turma}
                            </Text>
                            <Text style={{ color: theme.text }}>
                                <Text style={{ fontWeight: 'bold' }}>Contato:</Text> {selectedMember?.contato}
                            </Text>
                        </View>

                        <TouchableOpacity accessibilityRole="button" 
                            style={{ backgroundColor: '#0077B5', flexDirection: 'row', alignItems: 'center', paddingVertical: 12, width: '100%', justifyContent: 'center', borderRadius: 10 }}
                            onPress={() => selectedMember?.linkedin && Linking.openURL(selectedMember.linkedin)}
                        >
                            <FontAwesome5 name="linkedin" size={20} color="#FFF" />
                            <Text style={{ color: '#FFF', fontWeight: 'bold', marginLeft: 10 }}>VER LINKEDIN</Text>
                        </TouchableOpacity>

                    </View>
                </View>
            </Modal>

            {/* --- BANNER INFORMATIVO --- */}
            <View style={style.banner}>
                <View>
                    <Text style={style.bannerLabel}>UNIVERSITÁRIO</Text>
                    <Text style={style.bannerTitle}>Inovação Acadêmica</Text>
                </View>
                <View style={style.bannerIcon}>
                    <FontAwesome5 name="graduation-cap" size={20} color="#FFF" />
                </View>
            </View>

            {/* --- RODAPÉ --- */}
            <View style={style.footer}>
                <Text style={[style.footerBrand, { color: theme.text }]}>Nivelis Cursos</Text>
                <Text style={[style.copyright, { color: theme.subtext }]}>© 2026 Centro Universitário Augusto Motta</Text>
            </View>
        </ScrollView>
    );
}