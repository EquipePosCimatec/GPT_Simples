import streamlit as st
import os
import tempfile
from langchain.document_loaders import DirectoryLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.text_splitter import CharacterTextSplitter
from docx import Document
import sys
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import chromadb

try:
    chromadb.load_config("path/to/your/config.yaml")
except FileNotFoundError:
    st.error("Arquivo de configuração do ChromaDB não encontrado.")
except Exception as e:
    st.error(f"Erro ao carregar configurações do ChromaDB: {e}")





# Configuração inicial da API OpenAI
chave = st.secrets["KEY"]
os.environ["OPENAI_API_KEY"] = chave

# Templates de documentos
templates = {
    "DFD": {
        "1. OBJETO DA FUTURA CONTRATAÇÃO": "Indicação resumida do(s) bem, serviço ou obra a ser contratada",
        "2. UNIDADE SOLICITANTE": "Informar a Unidade que demandou a contratação",
        "3. UNIDADE GESTORA DO RECURSO (NOME E CÓDIGO):": "Informar a Unidade Gestora que suportará o custeio da despesa, indicando-a nominalmente e com o código orçamentário respectivo",
        "4. ORIGEM DO RECURSO": "Escolha entre RECURSOS PRÓPRIOS / RECURSOS ORIUNDOS DE CONVÊNIO ESTADUAL / RECURSOS ORIUNDOS DE CONVÊNIO FEDERAL",
        "5. PREVISÃO NO PLANO DE CONTRATAÇÃO ANUAL": "Informar SIM ou Não",
        "6. RESPONSÁVEL PELO PREENCHIMENTO DESTE DOCUMENTO": "Informar a Matricula / Nome Completo / Unidade Admnistrativa",
        "6. IDENTIFICAÇÃO DO SUPERIOR IMEDIATO": "Informar a Matricula / Nome Completo / Unidade Admnistrativa",
        
    },
    "ETP": {
        "1. DESCRIÇÃO DA NECESSIDADE DA CONTRATAÇÃO": "Este item destina-se a esclarecer especificamente o problema ou a carência que precisa ser solucionada (NECESSIDADE), priorizando o ponto de vista do bem-estar e interesse coletivo.",
        "2. PREVISÃO DA CONTRATAÇÃO NO PLANO DE CONTRATAÇÕES ANUAL – PCA": "Demonstre o alinhamento entre a contratação e o planejamento do MPBA, bem como identificação da previsão no Plano de Contratação Anual (PCA), ou, se for o caso, justificando a ausência de previsão neste plano.",
        "3. DESCRIÇÃO DOS REQUISITOS DA CONTRATAÇÃO": "Preencher o item OU apresentar JUSTIFICATIVA para a dispensa desta informação",
        "4. ESTIMATIVAS DAS QUANTIDADES PARA A CONTRATAÇÃO": "PREENCHER O ITEM OU APRESENTAR JUSTIFICATIVA PARA A DISPENSA DESTA INFORMAÇÃO",
        "5. LEVANTAMENTO DE MERCADO": "Indicar as possíveis alternativas de contratação (tipos de solução da demanda) existentes no mercado, para atendimento da necessidade informada;Indicar a alternativa escolhida;Justificar técnica e economicamente a escolha do tipo de solução a contratar.",
        "6. ESTIMATIVA DO VALOR DA CONTRATAÇÃO": "Informar a estimativa do valor total da contratação;Informar a estimativa dos valores unitários da contratação;Apresentar a memória de cálculo utilizada para a definição dos valores, e anexar ao processo SEI eventuais documentos que a embasaram.",
        "7. DESCRIÇÃO DA SOLUÇÃO": "PREENCHER O ITEM OU APRESENTAR JUSTIFICATIVA PARA A DISPENSA DESTA INFORMAÇÃO.",
        "8. PARCELAMENTO OU NÃO DA SOLUÇÃO": "PREENCHIMENTO OBRIGATÓRIO",
        "9. DESCRIÇÃO DA CONTRATAÇÃO": "PREENCHER O ITEM OU APRESENTAR JUSTIFICATIVA PARA A DISPENSA DESTA INFORMAÇÃO",
        "10. DESCRIÇÃO DA CONTRATAÇÃO": "PREENCHER O ITEM OU APRESENTAR JUSTIFICATIVA PARA A DISPENSA DESTA INFORMAÇÃO",
        "11. DESCRIÇÃO DA CONTRATAÇÃO": "PREENCHER O ITEM OU APRESENTAR JUSTIFICATIVA PARA A DISPENSA DESTA INFORMAÇÃO",
        "12. DESCRIÇÃO DA CONTRATAÇÃO": "PREENCHER O ITEM OU APRESENTAR JUSTIFICATIVA PARA A DISPENSA DESTA INFORMAÇÃO",
    },
    "TR": {
        "1. OBJETO": "Objeto da contratação",
        "2. JUSTIFICATIVA": "Justificativa para a contratação",
        
    }
}

# Funções de Processamento de Documentos

def preprocess_documents(directory_path):
    try:
        loader = DirectoryLoader(directory_path)
        documents = loader.load()
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        return text_splitter.split_documents(documents)
    except Exception as e:
        st.error(f"Erro ao carregar documentos: {str(e)}")
        return []

def preencher_documento(tipo_documento, retrieval_chain_config):
    if tipo_documento not in templates:
        raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")
    
    template = templates[tipo_documento]

    for campo in template:
        question = f"Por favor, me ajude a definir o/a {campo} com os dados que você tem acesso e com os dados da LLM."
        response = retrieval_chain_config.invoke({"question": question})
        template[campo] = response['answer']

    return template

def fill_documents_sequence(retrieval_chain_config, save_dir):
    sequencia_documentos = ["DFD", "ETP", "TR"]
    for tipo_documento in sequencia_documentos:
        documento_preenchido = preencher_documento(tipo_documento, retrieval_chain_config)
        save_document_txt(tipo_documento, documento_preenchido, save_dir)
        save_document_docx(tipo_documento, documento_preenchido, save_dir)

def save_document_txt(tipo_documento, conteudo, save_dir):
    caminho_txt = os.path.join(save_dir, f"{tipo_documento}.txt")
    with open(caminho_txt, 'w') as file:
        for campo, resposta in conteudo.items():
            file.write(f"{campo}: {resposta}\n")

def save_document_docx(tipo_documento, conteudo, save_dir):
    caminho_docx = os.path.join(save_dir, f"{tipo_documento}.docx")
    doc = Document()
    doc.add_heading(tipo_documento, 0)

    for campo, resposta in conteudo.items():
        doc.add_heading(campo, level=1)
        doc.add_paragraph(resposta)

    doc.save(caminho_docx)

def update_chroma_db(directory_path, db):
    loader = DirectoryLoader(directory_path)
    new_documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    new_docs = text_splitter.split_documents(new_documents)
    db.add_documents(new_docs)

# Interface do Streamlit

st.title("Gerador de Documentos com IA")

uploaded_files = st.file_uploader("Carregar Documentos", accept_multiple_files=True, type=["txt", "docx", "pdf"])

if uploaded_files:
    with st.spinner("Processando documentos..."):
        # Criar diretório temporário para armazenar arquivos
        temp_dir = tempfile.mkdtemp()

        for uploaded_file in uploaded_files:
            temp_file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(uploaded_file.read())

        # Carregar e processar documentos
        documents = preprocess_documents(temp_dir)
        if documents:
            st.success("Documentos carregados e processados com sucesso!")

            try:
                # Configurar embeddings e Chroma
                embedder = OpenAIEmbeddings()
                db = Chroma.from_documents(documents, embedder)

                # Configurar modelo de chat e memória
                chat_model = ChatOpenAI(temperature=0.7, model_name="gpt-4")
                memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

                # Configurar cadeia de recuperação conversacional
                retrieval_chain_config = ConversationalRetrievalChain.from_llm(
                    llm=chat_model,
                    chain_type="stuff",
                    retriever=db.as_retriever(),
                    memory=memory
                )

                # Preencher e salvar documentos
                fill_documents_sequence(retrieval_chain_config, temp_dir)
                st.success("Documentos preenchidos e salvos com sucesso!")

                # Mostrar documentos preenchidos
                for doc_type in ["DFD", "ETP", "TR"]:
                    with open(os.path.join(temp_dir, f"{doc_type}.txt"), "r") as file:
                        st.text(f"{doc_type}:\n" + file.read())

                # Atualizar Chroma DB
                update_chroma_db(temp_dir, db)
                st.success("Chroma DB atualizado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao configurar ChromaDB ou preencher documentos: {str(e)}")
        else:
            st.error("Nenhum documento foi processado devido a um erro.")
