import { StyleSheet } from 'react-native';

export const style = StyleSheet.create({
    // O container principal só precisa ocupar a tela toda
    container: {
        flex: 1,
    },
    // Criamos um novo estilo para o conteúdo interno do ScrollView
    scrollContent: {
        paddingHorizontal: 25,
        paddingTop: 60,
        paddingBottom: 80, // <-- O SEGREDO ESTÁ AQUI! Dá o espaço necessário para ver o rodapé
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 30,
    },
    // ... MANTENHA TODO O RESTANTE DOS SEUS ESTILOS INTACTOS ABAIXO ...
   iconButton: { padding: 10, borderRadius: 50 ,marginRight: 20 },

    backButton: {
        marginRight: 15,
    },
    headerTitle: {
        color: '#FFF',
        fontSize: 18,
        fontWeight: 'bold',
    },
    tagMission: {
        backgroundColor: 'rgba(124, 41, 229, 0.2)', // Roxo do seu padrão
        paddingHorizontal: 12,
        paddingVertical: 4,
        borderRadius: 20,
        alignSelf: 'flex-start',
        marginBottom: 15,
    },
    tagText: {
        color: '#7D53DD',
        fontSize: 10,
        fontWeight: 'bold',
    },
    title: {
        color: '#FFF',
        fontSize: 32,
        fontWeight: 'bold',
        lineHeight: 38,
    },
    titleHighlight: {
        color: '#7D53DD', 
    },
    description: {
        color: '#FFF',
        fontSize: 15,
        opacity: 0.7,
        marginTop: 15,
        lineHeight: 22,
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        marginTop: 40,
        marginBottom: 20,
    },
    sectionTitle: {
        color: '#FFF',
        fontSize: 20,
        fontWeight: 'bold',
    },
    memberCount: {
        color: '#7D53DD',
        fontSize: 10,
        fontWeight: 'bold',
    },
    teamContainer: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        gap: 12,
    },
    mainCard: {
        width: '100%',
        backgroundColor: '#1C1C1C', 
        padding: 20,
        borderRadius: 15,
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 5,
    },
    wideCard: {
        width: '100%',
        backgroundColor: '#1C1C1C',
        padding: 15,
        borderRadius: 15,
        flexDirection: 'row',
        alignItems: 'center',
    },
    smallCard: {
        width: '100%', // Ajustado para preencher o TouchableOpacity do map
        backgroundColor: '#1C1C1C',
        padding: 20,
        borderRadius: 15,
        alignItems: 'center',
    },
    avatarCircle: {
        width: 60,
        height: 60,
        borderRadius: 30,
        backgroundColor: '#333',
        overflow: 'hidden', // Garante que a imagem fique redonda
    },
    avatarSmall: {
        width: 45,
        height: 45,
        borderRadius: 22.5,
        backgroundColor: '#333',
        marginBottom: 8,
        overflow: 'hidden', // Garante que a imagem fique redonda
    },
    cardInfo: {
        marginLeft: 15,
        flex: 1,
    },
    memberNameLarge: {
        color: '#FFF',
        fontSize: 18,
        fontWeight: 'bold',
    },
    memberRoleHighlight: {
        color: '#7D53DD',
        fontSize: 12,
        fontWeight: 'bold',
        marginTop: 2,
    },
    memberNameSmall: {
        color: '#FFF',
        fontSize: 14,
        fontWeight: 'bold',
        textAlign: 'center',
    },
    memberRoleSmall: {
        color: '#FFF',
        fontSize: 10,
        opacity: 0.5,
        textAlign: 'center',
    },
    banner: {
        backgroundColor: '#7D53DD',
        borderRadius: 15,
        padding: 20,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginTop: 30,
    },
    bannerLabel: {
        color: 'rgba(255,255,255,0.6)',
        fontSize: 10,
        fontWeight: 'bold',
    },
    bannerTitle: {
        color: '#FFF',
        fontSize: 18,
        fontWeight: 'bold',
    },
    bannerIcon: {
        width: 40,
        height: 40,
        borderRadius: 10,
        backgroundColor: 'rgba(255,255,255,0.2)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    footer: {
        marginTop: 50,
        marginBottom: 40,
        alignItems: 'center',
    },
    footerBrand: {
        color: '#FFF',
        fontWeight: 'bold',
        fontSize: 16,
    },
    footerLinks: {
        color: '#7D53DD',
        fontSize: 12,
        marginVertical: 10,
    },
    copyright: {
        color: '#FFF',
        fontSize: 10,
        opacity: 0.4,
    },

    /* NOVAS ATUALIZAÇÕES PARA O MODAL */
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.85)',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 20,
    },
    modalContent: {
        backgroundColor: '#1C1C1C', // Mantendo o padrão dos cards
        width: '100%',
        borderRadius: 25,
        padding: 25,
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#333',
    },
    modalCloseButton: {
        alignSelf: 'flex-end',
        padding: 5,
    },
    modalImage: {
        width: 100,
        height: 100,
        borderRadius: 50,
        marginBottom: 15,
        borderWidth: 3,
        borderColor: '#7D53DD',
    },
    modalName: {
        color: '#FFF',
        fontSize: 22,
        fontWeight: 'bold',
    },
    modalRole: {
        color: '#7D53DD',
        fontSize: 14,
        fontWeight: 'bold',
        marginBottom: 20,
    },
    modalInfoSection: {
        width: '100%',
        backgroundColor: '#262626',
        borderRadius: 15,
        padding: 15,
        marginBottom: 20,
    },
    modalInfoText: {
        color: '#FFF',
        fontSize: 14,
        marginBottom: 8,
    },
    modalInfoLabel: {
        fontWeight: 'bold',
        color: '#7D53DD',
    },
    modalLinkedinButton: {
        backgroundColor: '#0077B5',
        width: '100%',
        padding: 15,
        borderRadius: 12,
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
    },
    modalLinkedinText: {
        color: '#FFF',
        fontWeight: 'bold',
        marginLeft: 10,
        fontSize: 14,
    }
});