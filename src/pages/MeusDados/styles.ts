import { StyleSheet, Platform } from 'react-native';

export const styles = StyleSheet.create({
  container: {
    flex: 1,
    // Background removido daqui para ser controlado pelo tema global no index.tsx
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 50,
    paddingBottom: 10,
  },
  scrollContent: {
    paddingHorizontal: 25,
    paddingBottom: 40,
  },
  profileSection: {
    alignItems: 'center',
    marginVertical: 30,
  },
  avatarWrapper: {
    position: 'relative',
    marginBottom: 15,
  },
  avatarContainer: {
    width: 130,
    height: 130,
    borderRadius: 65,
    borderWidth: 2,
    // Cor da borda e fundo agora são dinâmicos no index.tsx
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatar: {
    width: '100%',
    height: '100%',
    borderRadius: 65,
  },
  editPhotoBlock: {
    position: 'absolute',
    bottom: -5,
    right: -10,
    alignItems: 'center',
  },
  editPhotoIconCircle: {
    backgroundColor: '#7D53DD',
    width: 38,
    height: 38,
    borderRadius: 19,
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 3,
    // borderColor: '#12121b', <- REMOVIDO: Agora é controlado pelo theme.bg no index.tsx
    marginBottom: 2,
  },
  editPhotoText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '600',
    backgroundColor: 'rgba(124, 41, 229, 0.8)',
    paddingHorizontal: 6,
    borderRadius: 4,
    overflow: 'hidden',
  },
  userName: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  formSection: {
    marginTop: 10,
  },
  sectionTitle: {
    fontSize: 18,
    color: '#7D53DD',
    fontWeight: 'bold',
    marginBottom: 20,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 8,
    paddingHorizontal: 15,
    paddingVertical: 10,
    marginBottom: 15,
    height: 65,
    borderWidth: 1, // Ativado por padrão, a cor resolve a visibilidade
  },
  textWrapper: {
    flex: 1,
  },
  label: {
    fontSize: 12,
    marginBottom: 2,
  },
  input: {
    fontSize: 16,
    padding: 0,
  },
  inputSimple: {
    fontSize: 16,
    height: '100%',
  },
  inputDisabled: {
    opacity: 0.8,
  },
  textDisabled: {
    fontSize: 16,
  },
  saveButton: {
    backgroundColor: '#7D53DD',
    borderRadius: 8,
    height: 55,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 20,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  saveButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  menuContainer: {
    borderTopLeftRadius: 30,
    borderTopRightRadius: 30,
    paddingHorizontal: 20,
    paddingTop: 15,
    paddingBottom: Platform.OS === 'ios' ? 40 : 25,
    elevation: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -10 },
    shadowOpacity: 0.3,
    shadowRadius: 10,
  },
  dragIndicator: {
    width: 45,
    height: 5,
    backgroundColor: '#444',
    borderRadius: 10,
    alignSelf: 'center',
    marginBottom: 25,
    marginTop: 5,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 18,
    borderBottomWidth: 0.5,
    borderBottomColor: 'rgba(128, 128, 128, 0.2)',
  },
  menuText: {
    fontSize: 16,
    marginLeft: 15,
    fontWeight: '500',
  },
  versionText: {
    color: '#666',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 25,
    marginBottom: 5,
  },
});