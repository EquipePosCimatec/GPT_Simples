import streamlit as st
from io import BytesIO
from langchain.schema import Document as LangDocument
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from docx import Document
import docx2txt
import os
import re

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

        # Armazenar chunks em uma lista
        chunks = [doc.page_content for doc in docs]

        # Configurar o modelo de chat com GPT-4
        chat_model = ChatOpenAI(temperature=0.1, model_name="gpt-4-turbo")

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
        def preencher_documento(tipo_documento, chunks):
            inicial_instrução = """
              Considere que todo conteúdo gerado, é para o Ministério público do Estado
              da Bahia, logo as referências do documento devem ser para esse órgão.
            """
            if tipo_documento not in templates:
                raise ValueError(f"Tipo de documento {tipo_documento} não é suportado.")

            template = templates[tipo_documento]

            for campo, descricao in template.items():
                question = inicial_instrução + f" Preencha o {campo} que tem por descrição orientativa {descricao}."
                resposta = gerar_resposta(question, chunks)
                st.write(f"Resposta para {campo}:", resposta)  # Verificar a resposta gerada
                if resposta:
                    template[campo] = resposta
                else:
                    template[campo] = "Informação não encontrada nos documentos fornecidos."

            return template

        # Função para gerar respostas usando chunks
        def gerar_resposta(pergunta, chunks):
            # Simula a resposta baseada nos chunks
            contexto = "\n\n".join(chunks)
            prompt = f"Contexto: {contexto}\n\nPergunta: {pergunta}\nResposta:"
            messages = [{"role": "user", "content": prompt}]
            response = chat_model(messages)
            return response.choices[0].message["content"].strip()

        # Função para salvar documento em formato .docx
        def salvar_documento_docx(tipo_documento, conteudo):
            # Salvar em um diretório local acessível
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
                chunks = [anonimizar_texto(chunk) for chunk in chunks]  # Anonimizar texto dos chunks
                documento_preenchido = preencher_documento(tipo_documento, chunks)
                salvar_documento_docx(tipo_documento, documento_preenchido)
                st.write("Documento preenchido:", documento_preenchido)
