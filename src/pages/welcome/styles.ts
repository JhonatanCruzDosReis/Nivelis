import { StyleSheet, Dimensions } from 'react-native';

export const style = StyleSheet.create({
    container: {
        flex: 1,
        paddingHorizontal: 25,
        paddingTop: 60,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 50,
    },
    greetingText: {
        fontSize: 16,
        opacity: 0.8,
        // color removido
    },
    userName: {
        fontSize: 22,
        fontWeight: 'bold',
        // color removido
    },
    profileImage: {
        width: 50,
        height: 50,
        borderRadius: 25,
        alignItems: 'center',
        justifyContent: 'center',
        // backgroundColor e border controlados dinamicamente
    },
    logoContainer: {
        alignItems: 'center',
        marginBottom: 60,
    },
    logo: {
        width: 200,
        height: 200,
    },
    menuContainer: {
        gap: 15,
    },
    card: {
        width: '100%',
        height: 90,
        borderRadius: 12,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 20,
        // backgroundColor agora controlado no index.tsx
    },
    cardTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        // color removido
    },
    cardIconContainer: {
        width: 50,
        height: 50,
        borderRadius: 25,
        backgroundColor: 'rgba(124, 41, 229, 0.1)', 
        alignItems: 'center',
        justifyContent: 'center',
    }
});