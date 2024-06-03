import streamlit as st
from io import StringIO, BytesIO
from langchain.schema import Document as LangDocument
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Chroma
from docx import Document
import docx2txt
import os
import re

import sys

# Importe e manipule o módulo sqlite3
__import__('pysqlite3')
import pysqlite3
sys.modules['sqlite3'] = sys.modules["pysqlite3"]

# Agora você pode importar o chromadb
import chromadb

# Configuração inicial da API OpenAI
chave = st.secrets["KEY"]  # Assumindo que você configurou a chave nas variáveis de ambiente do Streamlit
os.environ["OPENAI_API_KEY"] = chave

# Layout e lógica do aplicativo Streamlit
st.title("Gerador de Documentos para o MPBA")

# Componente de upload de arquivos no Streamlit
uploaded_files = st.file_uploader("Carregue os arquivos", accept_multiple_files=True)

def read_file(file):
    if file.name.endswith('.docx'):
        return docx2txt.process(BytesIO(file.read()))
    else:
        try:
            return file.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            try:
                return file.getvalue().decode("latin-1")
            except UnicodeDecodeError:
                st.error(f"Não foi possível ler o arquivo {file.name}. Formato não suportado.")
                return None

if uploaded_files:
    documents = []
    # Ler o conteúdo dos arquivos carregados
    for uploaded_file in uploaded_files:
        content = read_file(uploaded_file)
        if content:
            documents.append(content)
    
    if documents:
        # Converter conteúdo dos arquivos para objetos LangDocument
        lang_docs = [LangDocument(page_content=doc) for doc in documents]

        # Dividir documentos em chunks
        text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=0)
        docs = text_splitter.split_documents(lang_docs)

        # Verificar os chunks gerados
        st.write("Chunks gerados:", docs)

        # Criar embedder com o modelo da OpenAI
        embedder = OpenAIEmbeddings(model="text-embedding-ada-002")

        # Verificar embeddings
        embeddings = embedder.embed_documents([doc.page_content for doc in docs])
        st.write("Embeddings gerados:", embeddings)

        try:
            # Criar ChromaDB com documentos e embedder (garantir nova coleção)
            db = Chroma.from_documents(docs, embedder, collection_name="document_collection_new")
            
            # Configurar o modelo de chat com GPT-4 e memória de conversação
            chat_model = ChatOpenAI(temperature=0.1, model_name="gpt-4-turbo")
            memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

            # Configurar a cadeia de recuperação conversacional
            retrieval_chain_config = ConversationalRetrievalChain.from_llm(
                llm=chat_model,
                chain_type="stuff",
                retriever=db.as_retriever(return_source_documents=True),
                memory=memory
            )

            # Definir templates de documentos
            templates = {
                "ETP": {
                    "1. DESCRIÇÃO DA NECESSIDADE DA CONTRATAÇÃO": "Este item visa clarificar o problema ou a deficiência...",
                    "2. PREVISÃO DA CONTRATAÇÃO NO PLANO DE CONTRATAÇÕES ANUAL – PCA": "Indique a inclusão desta contratação...",
                    "13. POSICIONAMENTO CONCLUSIVO SOBRE A CONTRATAÇÃO": "Forneça uma declaração final sobre a viabilidade..."
                },
                "TR": {
                    "1. OBJETO": "1 Aquisição de [inserir o objeto]...",
                    "1.1.2 PARCELAMENTO DA CONTRATAÇÃO": "REALIZADA EM ÚNICO ITEM...",
                    "4.1.3.2 GARANTIA DO PRODUTO, CONDIÇÕES DE MANUTENÇÃO E ASSISTÊNCIA TÉCNICA": "NÃO SE APLICA...",
                }
            }

            # Funções de anonimização
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

            # Função para preencher um documento com base no seu tipo
            def preencher_documento(tipo_documento, retrieval_chain_config):
                inicial_instrução = """
                  Considere que todo conteúdo gerado é para o Ministério Público do Estado
                  da Bahia, logo as referências do documento devem ser para esse órgão.
                """
                if tipo_documento not in templates:
                    raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")

                template = templates[tipo_documento]

                for campo, descricao in template.items():
                    question = inicial_instrução + f" Preencha o {campo} que tem por descrição orientativa {descricao}."
                    response = retrieval_chain_config.invoke({"question": question})
                    st.write(f"Resposta para {campo}:", response)  # Verificar a resposta gerada
                    if response and 'answer' in response:
                        template[campo] = response['answer']
                    else:
                        template[campo] = "Informação não encontrada nos documentos fornecidos."

                return template

            # Função para preencher um documento com base no seu tipo e retornar os chunks usados
            def preencher_documento_com_chunks(tipo_documento, retrieval_chain_config):
                inicial_instrução = """
                  Considere que todo conteúdo gerado é para o Ministério Público do Estado
                  da Bahia, logo as referências do documento devem ser para esse órgão.
                """
                if tipo_documento not in templates:
                    raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")

                template = templates[tipo_documento]
                chunk_references = {}

                for campo, descricao in template.items():
                    question = inicial_instrução + f" Preencha o {campo} que tem por descrição orientativa {descricao}."
                    response = retrieval_chain_config.invoke({"question": question})
                    st.write(f"Resposta para {campo}:", response)  # Verificar a resposta gerada
                    if response and 'answer' in response:
                        template[campo] = response['answer']
                        # Armazenar referências dos documentos usados
                        chunk_references[campo] = [doc.page_content for doc in response.get('source_documents', [])]
                    else:
                        template[campo] = "Informação não encontrada nos documentos fornecidos."
                        chunk_references[campo] = []

                return template, chunk_references

            # Função para salvar documento em formato .docx
            def salvar_documento_docx(tipo_documento, conteudo, chunk_references):
                # Salvar em um diretório local acessível
                caminho_docx = f"./artefatos/{tipo_documento}.docx"
                os.makedirs(os.path.dirname(caminho_docx), exist_ok=True)
                doc = Document()

                doc.add_heading(tipo_documento, level=1)

                for campo, resposta in conteudo.items():
                    doc.add_heading(campo, level=2)
                    doc.add_paragraph(resposta, style='BodyText')
                    # Adicionar referências dos chunks utilizados
                    if chunk_references[campo]:
                        doc.add_heading("Referências dos Chunks", level=3)
                        for chunk in chunk_references[campo]:
                            # Melhorar a formatação dos chunks
                            doc.add_paragraph(chunk, style='BodyText')

                doc.save(caminho_docx)
                st.success(f"{tipo_documento} salvo em {caminho_docx}")

            tipo_documento = st.selectbox("Selecione o tipo de documento", options=list(templates.keys()))

            if st.button("Preencher Documento"):
                with st.spinner("Preenchendo documento..."):
                    documento_preenchido, chunk_references = preencher_documento_com_chunks(tipo_documento, retrieval_chain_config)
                    salvar_documento_docx(tipo_documento, documento_preenchido, chunk_references)
                    st.write("Documento preenchido:", documento_preenchido)
                    st.write("Referências dos chunks utilizados:")
                    # Melhorar a formatação dos chunks ao exibir no Streamlit
                    for campo, chunks in chunk_references.items():
                        st.write(f"**{campo}:**")
                        for chunk in chunks:
                            st.write(f"- {chunk}")

        except Exception as e:
            st.error(f"Ocorreu um erro ao inicializar o ChromaDB: {e}")
