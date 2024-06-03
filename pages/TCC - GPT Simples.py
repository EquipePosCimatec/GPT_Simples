import streamlit as st
from io import BytesIO
from langchain.schema import Document as LangDocument
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Chroma
import docx2txt
from docx import Document
import os

# Configuração inicial da API OpenAI
chave = st.secrets["KEY"]
os.environ["OPENAI_API_KEY"] = chave

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
    for uploaded_file in uploaded_files:
        content = read_file(uploaded_file)
        if content:
            documents.append(content)

    if documents:
        # Converter conteúdo dos arquivos para objetos LangDocument
        lang_docs = [LangDocument(page_content=doc) for doc in documents]

        # Dividir documentos em chunks
        text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=0)
        chunks = text_splitter.split_documents(lang_docs)

        # Armazenar os chunks na sessão do Streamlit
        st.session_state.chunks = chunks

        # Exibir os chunks gerados
        st.write("Chunks gerados:")
        for i, chunk in enumerate(chunks):
            st.write(f"Chunk {i + 1}:")
            st.write(chunk.page_content)

        # Criar embedder com o modelo da OpenAI
        embedder = OpenAIEmbeddings(model="text-embedding-ada-002")
        embeddings = embedder.embed_documents([chunk.page_content for chunk in chunks])
        st.write("Embeddings gerados:", embeddings)

        # Criar ChromaDB com documentos e embedder (garantir nova coleção)
        db = Chroma.from_documents(chunks, embedder, collection_name="document_collection_new")
        
        # Configurar o modelo de chat com GPT-4 e memória de conversação
        chat_model = ChatOpenAI(temperature=0.1, model_name="gpt-4-turbo")
        memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

        # Configurar a cadeia de recuperação conversacional
        retrieval_chain = ConversationalRetrievalChain.from_llm(
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
            }
        }

        def preencher_documento_com_chunks(tipo_documento, chunks, retrieval_chain):
            inicial_instrução = """
              Considere que todo conteúdo gerado é para o Ministério Público do Estado
              da Bahia, logo as referências do documento devem ser para esse órgão.
            """
            if tipo_documento not in templates:
                raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")

            template = templates[tipo_documento]
            chunk_references = {}

            concatenated_chunks = "\n".join([chunk.page_content for chunk in chunks])

            for campo, descricao in template.items():
                question = inicial_instrução + f" Preencha o {campo} que tem por descrição orientativa: {descricao}."
                st.write(f"Question: {question}")

                # Combinar o contexto e a pergunta em uma única entrada
                input_text = f"{question}\n\n{concatenated_chunks}"
                
                # Debugging: Adicionar logs para verificar o formato dos inputs
                st.write(f"Input Text: {input_text}")

                try:
                    response = retrieval_chain({"input": input_text})
                    st.write(f"Resposta para {campo}:", response)

                    if response and 'output' in response:
                        template[campo] = response['output']
                        chunk_references[campo] = [chunk.page_content for chunk in chunks]
                    else:
                        template[campo] = "Informação não encontrada nos documentos fornecidos."
                        chunk_references[campo] = []
                except Exception as e:
                    st.error(f"Erro ao preencher {campo}: {e}")
                    template[campo] = "Erro ao gerar resposta."
                    chunk_references[campo] = []

            return template, chunk_references

        def salvar_documento_docx(tipo_documento, conteudo):
            caminho_docx = f"./artefatos/{tipo_documento}.docx"
            os.makedirs(os.path.dirname(caminho_docx), exist_ok=True)
            doc = Document()

            doc.add_heading(tipo_documento, level=1)
            for campo, resposta in conteudo.items():
                doc.add_heading(campo, level=2)
                doc.add_paragraph(resposta, style='BodyText')

            doc.save(caminho_docx)
            st.success(f"{tipo_documento} salvo em {caminho_docx}")

        tipo_documento = st.selectbox("Selecione o tipo de documento", options=list(templates.keys()))

        if st.button("Preencher Documento"):
            with st.spinner("Preenchendo documento..."):
                documento_preenchido, chunk_references = preencher_documento_com_chunks(tipo_documento, st.session_state.chunks, retrieval_chain)
                salvar_documento_docx(tipo_documento, documento_preenchido)
                st.write("Documento preenchido:", documento_preenchido)
                st.write("Referências dos chunks utilizados:", chunk_references)
