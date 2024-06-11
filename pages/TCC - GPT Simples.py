import os
import re
import shutil
import streamlit as st
from docx import Document as DocxDocument
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI

# Inicializar a variável global db_path
db_path = "/tmp/chroma_db"

# Função para salvar documento em formato .docx no PC do usuário
def salvar_documento_docx(tipo_documento, conteudo):
    caminho_docx = os.path.join("/tmp", f"{tipo_documento}.docx")
    doc = DocxDocument()

    doc.add_heading(tipo_documento, level=1)

    for campo, resposta in conteudo.items():
        doc.add_heading(campo, level=2)
        doc.add_paragraph(resposta, style='Normal')

    doc.save(caminho_docx)
    return caminho_docx

# Função para carregar um arquivo de texto com diferentes tentativas de codificação
def carregar_arquivo(file):
    codificacoes = ['utf-8', 'latin-1', 'cp1252']
    for encoding in codificacoes:
        try:
            file.seek(0)
            text = file.read().decode(encoding)
            return [Document(page_content=text)]
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Não foi possível carregar o arquivo com as codificações {codificacoes}")

# Função para reinicializar o chain com a memória reseta
def reinicializar_chain():
    return ConversationalRetrievalChain.from_llm(
        llm=chat_model,
        chain_type="map_reduce",
        retriever=db.as_retriever(return_source_documents=True, top_k=5),
        memory=ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    )

def anonimizar_nomes(texto):
    nomes_regex = r'\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b'
    texto_anonimizado = re.sub(nomes_regex, '[NOME]', texto)
    return texto_anonimizado

def anonimizar_emails(texto):
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    texto_anonimizado = re.sub(email_regex, '[EMAIL]', texto)
    return texto_anonimizado

def anonimizar_enderecos(texto):
    enderecos_regex = r'\d{1,4} [A-Z][a-z]+(?: [A-Z][a-z]+)*(?:, [A-Z]{2})? \d{5}'
    texto_anonimizado = re.sub(enderecos_regex, '[ENDEREÇO]', texto)
    return texto_anonimizado

def anonimizar_texto(texto):
    texto = anonimizar_nomes(texto)
    texto = anonimizar_emails(texto)
    texto = anonimizar_enderecos(texto)
    return texto

templates = {
    "ETP": {
      "1. DESCRIÇÃO DA NECESSIDADE DA CONTRATAÇÃO": "Descreva de forma detalhada a necessidade que leva à contratação, incluindo a situação atual, os problemas enfrentados e o impacto no bem-estar e interesse público. Quantifique e qualifique o problema, mencionando as unidades envolvidas e os esforços anteriores para resolver a questão.",
      "2. PREVISÃO DA CONTRATAÇÃO NO PLANO DE CONTRATAÇÕES ANUAL – PCA": "Indique se a contratação está prevista no Plano de Contratações Anual (PCA) do MPBA. Caso não esteja, justifique a ausência, fornecendo contexto e alternativas planejadas.",
    },
    "TR": {
      "1. OBJETO": "Descreva detalhadamente o objeto da contratação, incluindo condições, quantidades e especificações técnicas estabelecidas neste Termo de Referência e seus anexos.",
    }
}

# Função para limpar o banco de dados Chroma
def limpar_chroma_db(db_path):
    if os.path.exists(db_path):
        shutil.rmtree(db_path)
        print(f"Banco de dados Chroma em '{db_path}' foi excluído.")
    else:
        print(f"Banco de dados Chroma em '{db_path}' não encontrado.")

# Função para carregar novos documentos e recriar o banco de dados Chroma
def recriar_chroma_db(documents, db_path, embedder):
    # Limpar o banco de dados existente
    limpar_chroma_db(db_path)
    
    # Criar diretório se não existir
    os.makedirs(db_path, exist_ok=True)

    # Dividir documentos em chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=50)
    docs = text_splitter.split_documents(documents)
    
    # Criar e carregar o banco de dados Chroma
    db = Chroma.from_documents(docs, embedder, persist_directory=db_path)
    num_docs = len(db.get())
    print(f"Número de documentos no Chroma DB: {num_docs}")
    return db

# Função genérica para preencher documentos
def preencher_documento(tipo_documento, retrieval_chain_config):
    inicial_instrução = """
    Considere que todo conteúdo gerado deve atender aos requisitos do Ministério Público do Estado da Bahia,
    conforme as diretrizes e regulamentações estabelecidas pela Lei 14.133/2021. Ao preencher cada campo,
    leve em conta as particularidades desta legislação e a importância de alinhamento com o Plano de Contratações Anual (PCA)
    e outros normativos relevantes para licitações e contratos administrativos.
    As referências devem ser contextualizadas para o MPBA e suas necessidades específicas.
    """
    if tipo_documento not in templates:
        raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")

    template = templates[tipo_documento]

    for campo, descricao in template.items():
        question = inicial_instrução + f" Preencha o campo '{campo}' de acordo com a seguinte descrição orientativa: {descricao}. Certifique-se de que o preenchimento esteja em conformidade com a Lei 14.133/2021 e as diretrizes do Ministério Público do Estado da Bahia."
        response = retrieval_chain_config.invoke({"question": question})
        template[campo] = response['answer']

    return template

# Função para preencher a sequência de documentos
def preencher_sequencia_documentos(retrieval_chain_config, tipo_documento_selecionado):
    documento_preenchido = preencher_documento(tipo_documento_selecionado, retrieval_chain_config)
    caminho_salvo = salvar_documento(tipo_documento_selecionado, documento_preenchido)
    return caminho_salvo

# Função para salvar o documento em ambos os formatos e atualizar o Chroma DB
def salvar_documento(tipo_documento, conteudo):
    conteudo_anonimizado = {campo: anonimizar_texto(resposta) para campo, resposta em conteudo.items()}
    return salvar_documento_docx(tipo_documento, conteudo_anonimizado)

def iniciar_processo():
    global retrieval_chain_config, chat_model, db, documentos
    documentos = []
    file_paths = st.file_uploader("Selecione os arquivos que deseja processar", accept_multiple_files=True, key="file_uploader")
    if file_paths:
        for file em file_paths:
            documentos.extend(carregar_arquivo(file))

        # Set the API key as an environment variable
        os.environ["OPENAI_API_KEY"] = st.secrets["KEY"]
        
        embedder = OpenAIEmbeddings(model="text-embedding-3-large")
        db = recriar_chroma_db(documentos, db_path, embedder)
        
        chat_model = ChatOpenAI(temperature=0.5 , model_name="gpt-4o")
        memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
        retrieval_chain_config = reinicializar_chain()
        
        st.success("Documentos carregados e processados com sucesso.")
        st.write("Arquivos carregados:", [file.name para file em file_paths])
        return True
    return False

def gerar_documento(tipo_documento_selecionado):
    global retrieval_chain_config
    with st.spinner("Gerando documento, por favor aguarde..."):
        caminho_salvo = preencher_sequencia_documentos(retrieval_chain_config, tipo_documento_selecionado)
    st.success(f"Documento gerado com sucesso. Clique no link abaixo para baixar o arquivo.")
    with open(caminho_salvo, "rb") as file:
        btn = st.download_button(
            label="Baixar Documento",
            data=file,
            file_name=os.path.basename(caminho_salvo),
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    # Limpar o Chroma DB após o download do arquivo
    limpar_chroma_db(db_path)

# Interface do Streamlit
st.title("Gerador de Artefatos de Licitação do MPBA")

documentos_carregados = iniciar_processo()

if documentos_carregados:
    tipo_documento_selecionado = st.selectbox("Selecione o tipo de documento", list(templates.keys()), key="select_tipo_documento")
    if st.button("Gerar Documento", key="button_gerar_documento"):
        gerar_documento(tipo_documento_selecionado)
