import { Dimensions, StyleSheet } from "react-native";

// Capturamos a altura total da tela do celular do usuário
const { height } = Dimensions.get('window');

export const style = StyleSheet.create({
    container: {
        flex: 1, 
        alignItems: 'center', 
        justifyContent: 'center', 
        backgroundColor: '#000000' // Fundo totalmente branco para um visual limpo
    },

    /* --- 1º ANDAR: O TOPO (Identidade) --- */
    boxTop: {
        // É onde apresentamos a marca (Logo) e a saudação.
        height: height / 3, 
        width: '100%',
        alignItems: 'center', 
        justifyContent: 'center',
        paddingTop: 40 
    },

    /* --- 2º ANDAR: O MEIO (Interação) --- */
    boxMid: {
        // É o coração do formulário.
        // Aqui ficam os campos onde o usuário digita (Inputs).
        height: height / 4, 
        width: '100%',
        paddingHorizontal: 37, // Dá um respiro nas laterais para os campos não colarem na borda
    },

    /* --- 3º ANDAR: A BASE (Ação e Navegação) --- */
    boxBottom: {
        // Ocupa o restante da tela (1/3). Focado em finalizar o login.
        // Aqui colocamos o botão principal de "Entrar" e o link de cadastro.
        height: height / 3, 
        width: '100%',
        alignItems: 'center', 
        justifyContent: 'center'
    },

    /* --- ESTILOS DOS ELEMENTOS INTERNOS --- */
    
    logo: {
        width: 300,
        height: 200
    },
    text: {
        fontWeight: 'bold', 
        marginTop: 20,
        fontSize: 18,
        color: '#ebebebff'
    },
    tittleInput: {
        // Aquele texto pequeno em cima do campo (Ex: "ENDEREÇO DE E-MAIL")
        marginLeft: 5,
        color: '#fdfdfddc', 
        marginTop: 20,
        fontWeight: 'bold'
    },
    BoxInput: {
        // O "envelope" do campo. É aqui que desenhamos a borda e o fundo cinza claro.
        width: '100%',
        height: 50,
        borderWidth: 1, 
        borderRadius: 5, // Cantos levemente arredondados para um ar moderno
        borderColor: '#888888', 
        backgroundColor: '#000000', 
        marginTop: 10,
        flexDirection: 'row', // Faz o texto e o ícone ficarem na mesma linha (horizontal)
        alignItems: 'center',
        paddingHorizontal: 15
    },
    input: {
        // O campo invisível onde o usuário realmente digita as letras
        flex: 1, 
        height: '100%',
        color:'#ffffffff' // <--- ESTA LINHA define a cor do texto que o usuário digita
        
    },
    button: {
        // O botão de ação. Usamos azul e sombras para parecer clicável.
        width: '80%', 
        height: 50,
        backgroundColor: '#7D53DD', 
        borderRadius: 5,
        alignItems: 'center', 
        justifyContent: 'center',
        // Sombra para dar "volume" (profundidade) ao botão
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.25,
        shadowRadius: 3.84,
        elevation: 5, 
    },
    textButton: {
        color: '#FFF', 
        fontSize: 18,
        fontWeight: 'bold'
    },
    textBottom: {
        // Texto de rodapé (Ex: "Não tem conta?")
        fontSize: 16,
        color: '#555',
        marginTop: 20
    },
    textBottomBold: {
        // Estilo específico para destacar o link azul "Crie agora!"
        color: '#7D53DD', 
        fontWeight: 'bold'
    }
});