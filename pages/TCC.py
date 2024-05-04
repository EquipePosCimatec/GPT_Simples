import streamlit as st
from docx import Document
from openai import OpenAI

client = OpenAI()

# Configuração da chave API da OpenAI
openai.api_key = KEY

def extract_text_from_docx(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def retrieve_information(documents, query):
    # Implementação de uma busca simples nos documentos
    return "Informação relevante extraída dos documentos"

def generate_text_with_context(context, prompt):
    full_prompt = f"{context}\n\n{prompt}"
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",  # Substitua pelo modelo apropriado
        prompt=full_prompt,
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()

# Configuração da Interface Streamlit
st.title('Sistema de Enriquecimento de Prompts com RAG')

# Carregamento de Modelos de Documentos
st.header("Carregue seus modelos de documentos")
model_files = st.file_uploader("Escolha os modelos (arquivos Word)", accept_multiple_files=True, type='docx', key='models')

# Carregamento de Documentos de Conhecimento Adicional
st.header("Carregue documentos para a base de conhecimento adicional")
knowledge_files = st.file_uploader("Escolha documentos de conhecimento (arquivos Word, PDF, etc.)", accept_multiple_files=True, type=['docx', 'pdf'], key='knowledge')

# Entrada de prompt do usuário
st.header("Digite seu prompt")
user_query = st.text_input("Digite sua consulta")

if st.button('Gerar Resposta'):
    if model_files and user_query:
        # Processamento dos modelos de documentos
        model_content = [extract_text_from_docx(file) for file in model_files]
        # Processamento dos documentos de conhecimento adicional
        knowledge_content = [extract_text_from_docx(file) for file in knowledge_files] if knowledge_files else []

        # Combinação de conteúdos dos modelos e conhecimento adicional
        combined_content = "\n".join(model_content + knowledge_content)

        # Recuperação de informações baseada em todos os documentos carregados
        relevant_info = retrieve_information(combined_content, user_query)

        # Geração de texto com o prompt enriquecido
        answer = generate_text_with_context(relevant_info, user_query)
        st.write("Resposta:", answer)
    else:
        st.write("Por favor, carregue pelo menos um modelo de documento e digite uma consulta.")
