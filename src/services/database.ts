import { collection, addDoc, getDocs, doc, query, orderBy, writeBatch } from 'firebase/firestore';
import * as Sharing from 'expo-sharing';
import * as FileSystem from 'expo-file-system';

import { auth, db } from './firebase';

// Retorna a referência da sub-coleção de cronogramas do usuário logado
const getCronogramasRef = () => {
    const uid = auth.currentUser?.uid;
    if (!uid) throw new Error("Usuário não autenticado.");
    return collection(db, "users", uid, "cronogramas");
};

// Mantida para compatibilidade com App.tsx — Firestore não precisa de setup
export const setupDatabase = () => {
    console.log("[Nivelis] Firestore pronto. Nenhum setup de schema necessário.");
};

export async function adicionarCronogramaLocal(materia: string, topico: string, dataEstudo: string) {
    try {
        const ref = getCronogramasRef();
        await addDoc(ref, {
            materia,
            topico,
            data_estudo: dataEstudo,
            concluido: false,
            criadoEm: new Date().toISOString()
        });
        return { success: true };
    } catch (error) {
        console.error("Erro ao salvar cronograma no Firestore:", error);
        return { success: false, error };
    }
}

export async function listarCronogramasLocais() {
    try {
        const ref = getCronogramasRef();
        const q = query(ref, orderBy("data_estudo", "asc"));
        const snapshot = await getDocs(q);
        return snapshot.docs.map(d => ({ id: d.id, ...d.data() }));
    } catch (error) {
        console.error("Erro ao listar cronogramas do Firestore:", error);
        return [];
    }
}

export const limparBancoDeDados = async () => {
    try {
        const uid = auth.currentUser?.uid;
        if (!uid) return { success: false };

        const ref = getCronogramasRef();
        const snapshot = await getDocs(ref);
        const batch = writeBatch(db);

        snapshot.docs.forEach(document => {
            batch.delete(doc(db, "users", uid, "cronogramas", document.id));
        });

        await batch.commit();
        return { success: true };
    } catch (error) {
        console.error("Erro ao limpar cronogramas no Firestore:", error);
        return { success: false };
    }
};

export const exportarBancoDeDados = async () => {
    try {
        const cronogramas = await listarCronogramasLocais();
        const json = JSON.stringify(cronogramas, null, 2);
        const tempUri = FileSystem.cacheDirectory + 'nivelis_backup.json';

        await FileSystem.writeAsStringAsync(tempUri, json, {
            encoding: FileSystem.EncodingType.UTF8
        });

        await Sharing.shareAsync(tempUri, {
            dialogTitle: 'Exportar cronogramas (Nivelis)',
            mimeType: 'application/json',
        });
    } catch (error) {
        console.error("Erro ao exportar dados do Firestore:", error);
    }
};

export default db;
