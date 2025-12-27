import requests
import os
import shutil
from bs4 import BeautifulSoup
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIGURAÇÃO ---
WIKI_API_URL = "https://ordemparanormal.fandom.com/pt-br/api.php"
PASTA_SAIDA_DB = "cris_db_wiki"
# --------------------

def get_all_page_titles():
    """Busca os títulos de TODAS as páginas principais"""
    print("🌍 Consultando API para listar páginas...")
    titles = []
    params = {
        "action": "query", "format": "json", "list": "allpages",
        "aplimit": "500", "apnamespace": "0" 
    }
    while True:
        try:
            response = requests.get(WIKI_API_URL, params=params, timeout=10).json()
            if "query" in response:
                for page in response["query"]["allpages"]:
                    titles.append(page["title"])
            if "continue" in response:
                params["apcontinue"] = response["continue"]["apcontinue"]
            else:
                break
        except Exception as e:
            print(f"⚠️ Erro na API: {e}")
            break
    print(f"✅ Encontradas {len(titles)} páginas.")
    return titles

def extract_infobox_data(soup):
    """
    Extrai dados estruturados do 'Card' lateral (Infobox).
    Retorna uma string formatada: 'FICHA TÉCNICA: Apelidos: x, y...'
    """
    infobox_text = []
    
    # O padrão do Fandom é a classe 'portable-infobox'
    infoboxes = soup.find_all(class_="portable-infobox")
    
    for box in infoboxes:
        # Pega cada linha de dados (Rótulo + Valor)
        rows = box.find_all(class_="pi-data")
        
        for row in rows:
            label_tag = row.find(class_="pi-data-label")
            value_tag = row.find(class_="pi-data-value")
            
            if label_tag and value_tag:
                label = label_tag.get_text().strip()
                
                # Se o valor for uma lista (<ul>), separa por vírgula
                if value_tag.find("li"):
                    items = [li.get_text().strip() for li in value_tag.find_all("li")]
                    value = ", ".join(items)
                else:
                    # Tenta limpar quebras de linha estranhas
                    value = value_tag.get_text(" ", strip=True)
                
                infobox_text.append(f"- {label}: {value}")
                
        # Remove o infobox do HTML original para não duplicar o texto depois
        box.decompose()
        
    if infobox_text:
        return "=== FICHA TÉCNICA (CARD) ===\n" + "\n".join(infobox_text) + "\n==============================\n"
    return ""

def get_page_content(title):
    params = {
        "action": "parse", "format": "json", "page": title,
        "prop": "text", "redirects": 1
    }
    try:
        response = requests.get(WIKI_API_URL, params=params, timeout=10).json()
        if "parse" in response:
            html_raw = response["parse"]["text"]["*"]
            soup = BeautifulSoup(html_raw, "html.parser")
            
            # 1. Extrai o Card (Infobox) ANTES de limpar tudo
            infobox_data = extract_infobox_data(soup)
            
            # 2. Limpeza Geral (Remove menus, scripts, propagandas)
            for tag in soup(["script", "style", "aside", "nav", "figure", "table"]):
                # Cuidado: Se a Wiki usar tabelas para coisas importantes, tire "table" daqui.
                # Mas no Fandom, tabelas costumam ser lixo de navegação.
                tag.decompose()
                
            # 3. Pega o texto do corpo
            body_text = soup.get_text(separator="\n")
            
            # Limpa linhas vazias
            lines = [line.strip() for line in body_text.splitlines() if line.strip()]
            clean_body = "\n".join(lines)
            
            # Junta: Ficha Técnica + Conteúdo
            return infobox_data + "\n" + clean_body
            
    except Exception as e:
        print(f"❌ Erro ao processar '{title}': {e}")
    return None

def criar_banco_wiki_v2():
    titulos = get_all_page_titles()
    if not titulos: return

    documents = []
    print(f"📥 Baixando e processando Cards de {len(titulos)} páginas...")
    
    for i, titulo in enumerate(titulos):
        print(f"   [{i+1}/{len(titulos)}] {titulo}...")
        conteudo = get_page_content(titulo)
        
        if conteudo and len(conteudo) > 50:
            doc = Document(
                page_content=f"Sobre '{titulo}':\n{conteudo}",
                metadata={"source": f"Wiki: {titulo}"}
            )
            documents.append(doc)

    print(f"✅ Scraping finalizado. {len(documents)} páginas processadas.")

    # Limpa pasta antiga
    if os.path.exists(PASTA_SAIDA_DB):
        shutil.rmtree(PASTA_SAIDA_DB)

    print("🧠 Gerando Embeddings (Isso pode demorar)...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    docs_finais = text_splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = Chroma(
        persist_directory=PASTA_SAIDA_DB,
        embedding_function=embeddings,
        collection_name="foddaci_memory"
    )
    
    batch = 5000
    for i in range(0, len(docs_finais), batch):
        vector_db.add_documents(docs_finais[i:i+batch])
    
    print(f"🚀 SUCESSO! Banco V2 salvo em '{PASTA_SAIDA_DB}'.")
    print("Teste Rápido: Se você perguntar 'Quais os apelidos do Jean?', o bot deve saber.")

if __name__ == "__main__":
    criar_banco_wiki_v2()