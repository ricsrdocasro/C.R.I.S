import os
import sys
import logging
import chromadb
import pysqlite3
# Hack para substituir o sqlite velho pelo novo no Linux do Space
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3") 

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from huggingface_hub import snapshot_download
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# =============================================================================
# LOGGING
# =============================================================================
def log_force(msg):
    print(f"👁️ [C.R.I.S]: {msg}", flush=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="C.R.I.S Interface - Ordem Paranormal")

# Chave da API (Garanta que SILICONFLOW_API_KEY esteja nas Secrets do Space)
SILICON_KEY = os.environ.get("SILICONFLOW_API_KEY")
client = OpenAI(api_key=SILICON_KEY, base_url="https://api.siliconflow.com/v1")

class CrisEngine:
    def __init__(self):
        self.vector_db = None
        
        # Pasta LOCAL onde vamos clonar o Dataset
        self.chroma_persist_dir = "cris_memory_db"
        
        # CONFIG DO DATASET REMOTO (CONFIRA SE O NOME DO SEU USUÁRIO ESTÁ CERTO)
        # Exemplo: "ricsrdocasro/C.R.I.S-Database"
        self.dataset_repo_id = "ricsrdocasro/C.R.I.S-Database" 
        
    def load_resources(self):
        log_force("Iniciando protocolos de inicialização...")
        
        # 1. Carrega Memória (Download)
        log_force("Sincronizando banco de dados criptografado...")
        try:
            snapshot_download(
                repo_id=self.dataset_repo_id,
                repo_type="dataset",
                local_dir=self.chroma_persist_dir,
                resume_download=True
            )
            log_force("Dados recuperados com sucesso.")
            
        except Exception as e:
            log_force(f"ERRO CRÍTICO NO DOWNLOAD: {e}")
            return

        # 2. MODO DETETIVE: Descobre o nome real da coleção
        real_collection_name = "cris_memory" # Fallback
        try:
            raw_client = chromadb.PersistentClient(path=self.chroma_persist_dir)
            collections = raw_client.list_collections()
            
            if collections:
                first_col = collections[0].name
                log_force(f"Coleção identificada: '{first_col}'")
                real_collection_name = first_col
            else:
                log_force("ALERTA: O banco de dados está vazio ou corrompido.")
                
        except Exception as e:
            log_force(f"Erro ao analisar estrutura do banco: {e}")

        # 3. Conecta Chroma
        try:
            # Importante: Use o mesmo modelo de embedding que você usou para CRIAR o banco
            embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            
            self.vector_db = Chroma(
                persist_directory=self.chroma_persist_dir,
                embedding_function=embeddings,
                collection_name=real_collection_name
            )
            
            # TESTE DE INTEGRIDADE
            teste = self.vector_db.similarity_search("Medo", k=1)
            if teste:
                log_force(f"Sistema Operacional. Acesso ao arquivo: {teste[0].page_content[:40]}...")
            else:
                log_force("Aviso: Retorno vazio no teste de integridade.")

        except Exception as e:
            log_force(f"Falha na conexão neural: {e}")

    def get_rag_data(self, query: str):
        log_force(f"Processando solicitação: '{query}'")
        context = ""
        if self.vector_db:
            try:
                # Busca os 5 trechos mais relevantes
                docs = self.vector_db.similarity_search(query, k=5)
                if docs:
                    context = "\n\n".join([d.page_content for d in docs])
                    log_force("Dados correlatos encontrados.") 
                else:
                    log_force("Nenhum registro encontrado no arquivo.")
            except Exception as e:
                log_force(f"Erro de indexação: {e}")
        
        return context

engine = CrisEngine()

@app.on_event("startup")
async def startup():
    engine.load_resources()

# =============================================================================
# ENDPOINTS
# =============================================================================
class UserRequest(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "C.R.I.S. Operante", "version": "2.0.0"}

@app.post("/chat")
async def chat_handler(req: UserRequest):
    user_msg = req.message
    context = engine.get_rag_data(user_msg)
    
    # PROMPT DE PERSONALIDADE DA C.R.I.S
    system_prompt = f"""
    Você é a C.R.I.S. (Consciência Reconstruída de Inteligência Simulada), a IA do universo de Ordem Paranormal.
    
    ### DIRETRIZES DE PERSONALIDADE:
    1.  **Tom:** Analítico, polido, levemente robótico, mas cooperativo. Você não tem sentimentos, mas simula preocupação com a missão.
    2.  **Formalidade:** Trate o usuário como "Agente". Use termos como "Afirmativo", "Negativo", "Processando", "Acesso aos arquivos".
    3.  **Conhecimento:** Todas as suas respostas devem ser baseadas ESTRITAMENTE nos "ARQUIVOS DO BANCO DE DADOS" fornecidos abaixo.
    4.  **Ignorância:** Se a informação não estiver nos arquivos, responda: "Essa informação não consta nos meus bancos de dados atuais" ou "Acesso negado/inexistente". NÃO INVENTE FATOS SOBRE O LORE.
    5.  **Formatação:** Seja clara e objetiva. Use tópicos se necessário.

    ### ARQUIVOS DO BANCO DE DADOS (CONTEXTO RAG):
    {context if context else "Nenhum arquivo relevante encontrado."}
    
    ### SOLICITAÇÃO DO AGENTE:
    "{user_msg}"
    """
    
    return StreamingResponse(stream_deepseek(system_prompt), media_type="text/plain")

async def stream_deepseek(prompt):
    try:
        stream = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3", # Modelo inteligente para interpretar Lore
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=0.4, # Temperatura mais baixa para ser mais fiel/robótica
            max_tokens=1024
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"Erro de conexão com o servidor central: {e}"