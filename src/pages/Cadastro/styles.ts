import { Dimensions, StyleSheet } from "react-native";

/**
 * CONFIGURAÇÃO DE DIMENSÕES
 * Capturamos a altura (height) da tela do dispositivo para criar layouts 
 * responsivos que se adaptam a diferentes tamanhos de celular.
 */
const { height } = Dimensions.get('window');

export const style = StyleSheet.create({
    // --- LAYOUT BASE ---
    container: {
        flex: 1,               // Faz o container ocupar toda a tela disponível
        backgroundColor: '#000', // Fundo preto total
        paddingHorizontal: 30, // Espaçamento interno nas laterais
    },

    // --- CABEÇALHO (HEADER) ---
    header: {
        // Define a altura baseada em 20% do tamanho total da tela do celular
        height: height * 0.20, 
        justifyContent: 'center', // Alinha o conteúdo verticalmente ao centro
        paddingTop: 30,
    },
    backButton: {
        position: 'absolute' ,
        width: 35,
        height: 35,
        borderRadius: 18,      // Metade do width/height para deixar o botão circular
        backgroundColor: '#FFF',
        alignItems: 'center',    // Alinha o ícone horizontalmente
        justifyContent: 'center', // Alinha o ícone verticalmente
        marginBottom: 15,
        marginTop: 50    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#FFF',
        marginTop: 50
    },
    subtitle: {
        fontSize: 14,
        color: '#888',
        marginTop: 20,
    },

    // --- FORMULÁRIO (ÁREA DE INPUTS) ---
    form: {
        flex: 1,
        marginTop: 20, 
    },
    inputContainer: {
        width: '100%',
        height: 55, 
        borderWidth: 1,
        borderColor: '#888888', 
        borderRadius: 5,
        flexDirection: 'row',    // Coloca o TextInput e o Ícone lado a lado
        alignItems: 'center',    // Centraliza os itens verticalmente dentro da linha
        paddingHorizontal: 15,
        marginBottom: 12, 
    },
    input: {
        flex: 1,                // Faz o campo de texto ocupar todo o espaço restante da linha
        color: '#FFF',
        fontSize: 15,
    },

    // --- SEÇÃO DE TERMOS E CONDIÇÕES (CHECKBOX) ---
    termsContainer: {
        flexDirection: 'row',    // Alinha o quadrado da checkbox com o texto
        alignItems: 'center',
        marginTop: 10,
        marginBottom: 20, 
    },
    checkbox: {
        width: 20,
        height: 20,
        borderWidth: 1,
        borderColor: '#7D53DD',
        borderRadius: 4,
        marginRight: 10,
        alignItems: 'center',
        justifyContent: 'center',
    },
    termsText: {
        color: '#888',
        fontSize: 14,
    },

    // --- BOTÕES E AÇÕES ---
    button: {
        width: '100%',
        height: 55,
        backgroundColor: '#7D53DD', 
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
        marginTop: 20, 
        marginBottom: 40, 
    },
    buttonText: {
        color: '#FFF',
        fontSize: 16,
        fontWeight: 'bold',
        //textTransform: 'uppercase' // Transforma o texto em LETRAS MAIÚSCULAS
    }
});