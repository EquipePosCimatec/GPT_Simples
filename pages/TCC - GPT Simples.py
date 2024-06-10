import os
import re
import streamlit as st
from docx import Document as DocxDocument
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI

# Função para salvar documento em formato .docx no PC do usuário
def salvar_documento_docx(tipo_documento, conteudo):
    user_home = os.path.expanduser("~")
    caminho_docx = os.path.join(user_home, "Downloads", "Artefatos", f"{tipo_documento}.docx")
    os.makedirs(os.path.dirname(caminho_docx), exist_ok=True)
    doc = DocxDocument()

    doc.add_heading(tipo_documento, level=1)

    for campo, resposta in conteudo.items():
        doc.add_heading(campo, level=2)
        doc.add_paragraph(resposta, style='Normal')

    doc.save(caminho_docx)
    print(f"{tipo_documento} salvo em {caminho_docx}")
    return caminho_docx

# Função para carregar um arquivo de texto com diferentes tentativas de codificação
def carregar_arquivo(file_path):
    codificacoes = ['utf-8', 'latin-1', 'cp1252']
    for encoding in codificacoes:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                text = f.read()
            return [Document(page_content=text)]
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"Não foi possível carregar o arquivo: {file_path} com as codificações {codificacoes}")

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
      "3. DESCRIÇÃO DOS REQUISITOS DA CONTRATAÇÃO": "Especifique os requisitos técnicos e de desempenho necessários para a contratação, incluindo padrões de qualidade, prazos de implementação e restrições de marca ou produto, com as devidas justificativas.",
      "4. ESTIMATIVAS DAS QUANTIDADES PARA A CONTRATAÇÃO": "Apresente uma estimativa detalhada das quantidades necessárias, baseada em consumo histórico e projeções futuras. Inclua memórias de cálculo e justifique cada quantidade com dados concretos.",
      "5. LEVANTAMENTO DE MERCADO": "Realize uma pesquisa de mercado para identificar as melhores opções disponíveis. Apresente uma análise técnica e econômica das opções e justifique a escolha da solução mais vantajosa.",
      "6. ESTIMATIVA DO VALOR DA CONTRATAÇÃO": "Informe a estimativa de valor total e unitário da contratação, com base em pesquisa de mercado e análises comparativas de custo. Anexe a memória de cálculo e documentos de suporte.",
      "7. DESCRIÇÃO DA SOLUÇÃO": "Descreva detalhadamente a solução escolhida, incluindo todos os componentes essenciais e acessórios necessários. Inclua expectativas de manutenção, suporte técnico e treinamento.",
      "8. PARCELAMENTO OU NÃO DA SOLUÇÃO": "Indique se a solução será adquirida integralmente ou parcelada, justificando a escolha com base em eficiência logística, custos e gestão de recursos.",
      "9. RESULTADOS PRETENDIDOS COM A CONTRATAÇÃO": "Defina os benefícios esperados com a contratação, como redução de custos, aumento de eficiência e melhorias ambientais. Justifique cada resultado esperado com base em análises técnicas e econômicas.",
      "10. PROVIDÊNCIAS A SEREM ADOTADAS PELA ADMINISTRAÇÃO PREVIAMENTE À CONTRATAÇÃO": "Identifique as ações necessárias antes da contratação para garantir a implementação eficaz da solução, como ajustes no ambiente físico ou atualizações tecnológicas.",
      "11. CONTRATAÇÕES CORRELATAS E/OU INTERDEPENDENTES": "Liste quaisquer contratações relacionadas ou interdependentes, detalhando a interligação e influência mútua em seus desempenhos.",
      "12. POSSÍVEIS IMPACTOS AMBIENTAIS": "Analise os impactos ambientais da contratação, considerando o consumo de recursos e a disposição final dos materiais. Proponha medidas para minimizar efeitos negativos e fomentar práticas sustentáveis.",
      "13. POSICIONAMENTO CONCLUSIVO SOBRE A CONTRATAÇÃO": "Forneça uma declaração final sobre a viabilidade e necessidade da contratação, baseada em estudos técnicos e análises realizadas, afirmando se a contratação deve prosseguir conforme planejado.",
    },
    "TR": {
      "1. OBJETO": "Descreva detalhadamente o objeto da contratação, incluindo condições, quantidades e especificações técnicas estabelecidas neste Termo de Referência e seus anexos.",
      "1.1.2 PARCELAMENTO DA CONTRATAÇÃO": "Indique se a contratação será realizada em um único item, dividida em itens ou lotes. Justifique a escolha do parcelamento ou do agrupamento em lotes.",
      "1.1.3 INDICAÇÃO DE MARCAS OU MODELOS": "Especifique se há indicação de marcas ou modelos específicos. Justifique a necessidade de exclusividade ou referência de marcas/modelos, se aplicável.",
      "1.1.4 A VEDAÇÃO DE CONTRATAÇÃO DE MARCA OU PRODUTO": "Indique se há vedação para contratação de determinadas marcas ou produtos, justificando a restrição.",
      "1.2 NATUREZA DO OBJETO": "Classifique o objeto como de natureza comum ou especial, conforme sua especificidade e aplicação.",
      "1.3 ENQUADRAMENTO, VIGÊNCIA E FORMALIZAÇÃO DA CONTRATAÇÃO": "Indique se a contratação é de natureza continuada ou não continuada, e detalhe o prazo de vigência e a forma de formalização do contrato.",
      "1.3.2 PRAZO DE VIGÊNCIA": "Especifique o prazo de vigência do contrato, incluindo datas de início e término.",
      "1.3.3 FORMALIZAÇÃO DA CONTRATAÇÃO": "Detalhe a forma de formalização da contratação, como emissão de instrumento substitutivo ao contrato, celebração de contrato formal, ou celebração de Ata de Registro de Preços.",
      "2. FUNDAMENTAÇÃO DA CONTRATAÇÃO": "Justifique a necessidade da contratação, baseando-se em estudos técnicos, análises de mercado e dados específicos que respaldam a decisão.",
      "3. DESCRIÇÃO DA SOLUÇÃO": "Descreva a solução proposta de forma abrangente, incluindo componentes, funcionalidades e qualquer especificidade técnica relevante.",
      "4. REQUISITOS DA CONTRATAÇÃO": "Liste os requisitos técnicos, de desempenho e de qualidade que a solução contratada deve atender.",
      "4.1.1 SUSTENTABILIDADE": "Indique se a contratação incorpora critérios de sustentabilidade no contexto de ESG (Ambiental, Social e Governança). Justifique a inclusão ou exclusão desses critérios.",
      "4.1.2 SUBCONTRATAÇÃO": "Especifique se será admitida a subcontratação do objeto contratual, parcial ou integralmente, e as condições para tal.",
      "4.1.3 - GARANTIAS": "Detalhe as garantias exigidas para a execução do contrato e para os produtos adquiridos, incluindo manutenção e assistência técnica.",
      "4.1.3.1 GARANTIA DA EXECUÇÃO CONTRATUAL": "Indique se será exigida garantia contratual para a execução do contrato.",
      "4.1.3.2 GARANTIA DO PRODUTO, CONDIÇÕES DE MANUTENÇÃO E ASSISTÊNCIA TÉCNICA": "Detalhe as garantias do produto, incluindo condições de manutenção e assistência técnica, se aplicáveis.",
      "5. MODELO DE EXECUÇÃO DO OBJETO": "Descreva o modelo de execução do objeto da contratação, incluindo etapas, cronograma e responsabilidades.",
      "5.1 PRAZO PARA RETIRADA DO EMPENHO": "Especifique o prazo para a retirada do empenho após a formalização do contrato.",
      "5.2 PRAZO E FORMA DE ENTREGA": "Detalhe o prazo e a forma de entrega dos produtos ou serviços contratados.",
      "5.4 RECEBIMENTO DO OBJETO": "Descreva o processo de recebimento do objeto, incluindo condições e procedimentos para aceitação provisória e definitiva.",
      "5.4.1 RECEBIMENTO PROVISÓRIO": "Especifique as condições para o recebimento provisório do objeto contratado.",
      "5.4.2 RECEBIMENTO DEFINITIVO": "Detalhe os critérios e condições para o recebimento definitivo do objeto, após a verificação do cumprimento de todas as exigências contratuais.",
      "5.4.3 DEMAIS REGRAMENTOS": "Inclua quaisquer outros regramentos pertinentes ao processo de execução e recebimento do objeto da contratação.",
    }
}

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

    print(f"RESPOSTA INTEGRAL para {tipo_documento}:", template)
    return template

# Função para preencher a sequência de documentos
def preencher_sequencia_documentos(retrieval_chain_config, tipo_documento_selecionado):
    documento_preenchido = preencher_documento(tipo_documento_selecionado, retrieval_chain_config)
    caminho_salvo = salvar_documento(tipo_documento_selecionado, documento_preenchido)
    return caminho_salvo

# Função para salvar o documento em ambos os formatos e atualizar o Chroma DB
def salvar_documento(tipo_documento, conteudo):
    conteudo_anonimizado = {campo: anonimizar_texto(resposta) for campo, resposta in conteudo.items()}
    return salvar_documento_docx(tipo_documento, conteudo_anonimizado)

def iniciar_processo():
    global retrieval_chain_config, chat_model, db
    file_paths = st.file_uploader("Selecione os arquivos que deseja processar", accept_multiple_files=True)
    if not file_paths:
        st.warning("Nenhum arquivo selecionado.")
        return
    
    documentos = []
    for file_path in file_paths:
        documentos.extend(carregar_arquivo(file_path))

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=50)
    docs = text_splitter.split_documents(documentos)

    # Set the API key as an environment variable
    os.environ["OPENAI_API_KEY"] = KEY
    
    embedder = OpenAIEmbeddings(model="text-embedding-3-large")
    db = Chroma.from_documents(docs, embedder)
    
    chat_model = ChatOpenAI(temperature=0.5, model_name="gpt-4o")
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    retrieval_chain_config = reinicializar_chain()
    
    st.success("Documentos carregados e processados com sucesso.")

def gerar_documento():
    tipo_documento_selecionado = st.selectbox("Selecione o tipo de documento", list(templates.keys()))
    if not tipo_documento_selecionado:
        st.warning("Nenhum tipo de documento selecionado.")
        return

    st.info("Gerando documento, por favor aguarde...")

    try:
        caminho_salvo = preencher_sequencia_documentos(retrieval_chain_config, tipo_documento_selecionado)
        st.success(f"Documento gerado com sucesso. Clique no caminho abaixo para ser direcionado à pasta onde o arquivo foi salvo.")
        st.write(caminho_salvo)
        
    except Exception as e:
        st.error(f"Erro ao gerar documento: {str(e)}")

# Interface do Streamlit
st.title("Gerador de Artefatos de Licitação do MPBA")

if st.button("1. Selecione os seus documentos"):
    iniciar_processo()

if st.button("3. Gerar Documento"):
    gerar_documento()
