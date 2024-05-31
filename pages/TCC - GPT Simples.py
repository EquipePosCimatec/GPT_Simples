import streamlit as st
from io import StringIO
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from docx import Document
import os
import re

# Configuração inicial da API OpenAI
chave = st.secrets["KEY"]
client = OpenAI(api_key = chave)

# Layout e lógica do aplicativo Streamlit
st.title("Gerador de Documentos para o MPBA")

# Componente de upload de arquivos no Streamlit
uploaded_files = st.file_uploader("Carregue os arquivos", accept_multiple_files=True)

if uploaded_files:
    documents = []
    # Ler o conteúdo dos arquivos carregados
    for uploaded_file in uploaded_files:
        content = StringIO(uploaded_file.getvalue().decode("utf-8")).read()
        documents.append(content)
    
    # Converter documentos carregados para o formato langchain e dividir em chunks
    text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=0)
    docs = []

    for content in documents:
        loader = TextLoader(content)
        doc = loader.load()
        chunks = text_splitter.split_documents(doc)
        docs.extend(chunks)

    # Criar embedder com o modelo da OpenAI
    embedder = OpenAIEmbeddings(model="text-embedding-3-large")

    # Carregar Chroma com documentos e embedder
    db = Chroma.from_documents(docs, embedder)

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
            "3. DESCRIÇÃO DOS REQUISITOS DA CONTRATAÇÃO": "Especifique todos os requisitos técnicos e de desempenho necessários...",
            "4. ESTIMATIVAS DAS QUANTIDADES PARA A CONTRATAÇÃO": "Baseando-se em consumo real e projeções futuras...",
            "5. LEVANTAMENTO DE MERCADO": "Realize uma pesquisa comparativa de mercado...",
            "6. ESTIMATIVA DO VALOR DA CONTRATAÇÃO": "Informe a estimativa do valor total e unitário da contratação...",
            "7. DESCRIÇÃO DA SOLUÇÃO": "Descreva a solução escolhida de forma abrangente...",
            "8. PARCELAMENTO OU NÃO DA SOLUÇÃO": "Discuta se a solução será parcelada ou adquirida integralmente...",
            "9. RESULTADOS PRETENDIDOS COM A CONTRATAÇÃO": "Defina os benefícios diretos e indiretos esperados...",
            "10. PROVIDÊNCIAS A SEREM ADOTADAS PELA ADMINISTRAÇÃO PREVIAMENTE À CONTRATAÇÃO": "Identifique quaisquer ações necessárias...",
            "11. CONTRATAÇÕES CORRELATAS E/OU INTERDEPENDENTES": "Liste quaisquer contratações relacionadas...",
            "12. POSSÍVEIS IMPACTOS AMBIENTAIS": "Analise os impactos ambientais da contratação...",
            "13. POSICIONAMENTO CONCLUSIVO SOBRE A CONTRATAÇÃO": "Forneça uma declaração final sobre a viabilidade..."
        },
        "TR": {
            "1. OBJETO": "1 Aquisição de [inserir o objeto]...",
            "1.1.2 PARCELAMENTO DA CONTRATAÇÃO": "REALIZADA EM ÚNICO ITEM...",
            "1.1.3 INDICAÇÃO DE MARCAS OU MODELOS": "NÃO SE APLICA / EXCLUSIVIDADE DE MARCA/MODELO...",
            "1.1.4 A VEDAÇÃO DE CONTRATAÇÃO DE MARCA OU PRODUTO": "NÃO SE APLICA / SE APLICA",
            "1.2 NATUREZA DO OBJETO": "NATUREZA COMUM / NATUREZA ESPECIAL",
            "1.3 ENQUADRAMENTO, VIGÊNCIA E FORMALIZAÇÃO DA CONTRATAÇÃO": "NÃO CONTINUADO / CONTINUADO",
            "1.3.2 PRAZO DE VIGÊNCIA": "",
            "1.3.3 FORMALIZAÇÃO DA CONTRATAÇÃO": "HAVERÁ SOMENTE EMISSÃO DE INSTRUMENTO SUBSTITUTIVO...",
            "2. FUNDAMENTAÇÃO DA CONTRATAÇÃO": "",
            "3. DESCRIÇÃO DA SOLUÇÃO": "",
            "4. REQUISITOS DA CONTRATAÇÃO": "",
            "4.1.1 SUSTENTABILIDADE": "APLICAM-SE CRITÉRIOS DE SUSTENTABILIDADE...",
            "4.1.2 SUBCONTRATAÇÃO": "NÃO SERÁ ADMITIDA A SUBCONTRATAÇÃO...",
            "4.1.3 - GARANTIAS": "",
            "4.1.3.1 GARANTIA DA EXECUÇÃO CONTRATUAL": "NÃO SERÁ EXIGIDA GARANTIA CONTRATUAL...",
            "4.1.3.2 GARANTIA DO PRODUTO, CONDIÇÕES DE MANUTENÇÃO E ASSISTÊNCIA TÉCNICA": "NÃO SE APLICA...",
            "5. MODELO DE EXECUÇÃO DO OBJETO": "",
            "5.1 PRAZO PARA RETIRADA DO EMPENHO": "",
            "5.2 PRAZO E FORMA DE ENTREGA": "",
            "5.4 RECEBIMENTO DO OBJETO": "",
            "5.4.1 RECEBIMENTO PROVISÓRIO": "",
            "5.4.2 RECEBIMENTO DEFINITIVO": "",
            "5.4.3 DEMAIS REGRAMENTOS": ""
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
          Considere que todo conteúdo gerado, é para o Ministério público do Estado
          da Bahia, logo as referênicas do documento dever ser para esse órgão.
        """
        if tipo_documento not in templates:
            raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")

        template = templates[tipo_documento]

        for campo, descricao in template.items():
            question = inicial_instrução + f" Preencha o {campo} que tem por descrição orientativa {descricao}."
            response = retrieval_chain_config.invoke({"question": question})
            template[campo] = response['answer']

        return template

    # Função para salvar documento em formato .docx
    def salvar_documento_docx(tipo_documento, conteudo):
        caminho_docx = f"/content/drive/My Drive/Artefados/{tipo_documento}.docx"
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
            documento_preenchido = preencher_documento(tipo_documento, retrieval_chain_config)
            salvar_documento_docx(tipo_documento, documento_preenchido)
            st.write(documento_preenchido)
