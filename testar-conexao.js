// esse arquivo é só para conferir se o firebase está funcioando , coloque "node testar-conexão.js" e verifique no fire base , se quiser pode até remover o arquivo
import { db } from './firebase-config.js';
import { collection, addDoc } from "firebase/firestore"; 

async function enviarDadosParaFirebase() {
  try {
    console.log("Tentando conectar ao Firebase...");
    
    // Vamos criar uma coleção chamada 'usuarios' e salvar um documento lá
    const docRef = await addDoc(collection(db, "usuarios"), {
      nome: "Coloque_seu_nome_aqui",
      descricao: "Teste de conexão via API",
      tecnologias: ["Firebase", "Node.js", "React Native"],
      dataEnvio: new Date().toISOString()
    });

    console.log("✅ Sucesso! Dados gravados com o ID:", docRef.id);
  } catch (erro) {
    console.error("❌ Erro ao conectar ou gravar dados:", erro);
  }
}

enviarDadosParaFirebase();