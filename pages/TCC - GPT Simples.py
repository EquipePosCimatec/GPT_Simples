import streamlit as st
import openai
from io import BytesIO
from docx import Document
from openai import OpenAI
from PIL import Image
import docx
import docx2txt

# Configuração inicial da API OpenAI
chave = st.secrets["KEY"]
client = OpenAI(api_key=chave)

def extract_text_from_docx(file):
    try:
        text = docx2txt.process(file)
        return text
    except Exception as e:
        print(f"Error extracting text from {file}: {e}")
        return None

def retrieve_information(documents, query):
    # Implementação de uma busca simples nos documentos
    return "Informação relevante extraída dos documentos"

def generate_text_with_context(context, prompt):
    full_prompt = f"{context}\n\n{prompt}"
    try:
        # Uso correto da API de chat completions
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "Você será um especialista em criar artefatos de licitação Documento de Formalização da Demanda (DFD), Estudo Técnico Preliminar (ETP) e Termo de Referência (TR)"},
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Erro ao gerar texto com o chat: {e}")
        return e


# Configuração da Interface Streamlit
st.title('Sistema de Automatização do Artefatos de contratação com RAG')

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
        errors = []
        model_content = []
        knowledge_content = []

        # Processamento dos modelos de documentos
        for file in model_files:
            text = extract_text_from_docx(file)
            if text is not None:
                model_content.append(text)
            else:
                errors.append(f"Erro ao extrair texto do arquivo {file.name}")

        # Processamento dos documentos de conhecimento adicional
        for file in knowledge_files:
            text = extract_text_from_docx(file)
            if text is not None:
                knowledge_content.append(text)
            else:
                errors.append(f"Erro ao extrair texto do arquivo {file.name}")

        # Combinação de conteúdos dos modelos e conhecimento adicional
        combined_content = "\n".join(model_content + knowledge_content)

        # Geração de texto com o prompt enriquecido
        answer = generate_text_with_context(combined_content, user_query)
        
        if isinstance(answer, str):
            st.write("Resposta:", answer)
        else:
            errors.append("Erro ao gerar a resposta")

        if errors:
            st.error("Erros encontrados:\n" + "\n".join(errors))
    else:
        st.error("Por favor, carregue pelo menos um modelo de documento e digite uma consulta.")
