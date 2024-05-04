import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
from openai import OpenAI

# 1. Classe PDF personalizada com cabeçalho e rodapé
class PDF(FPDF):
    def header(self):
        self.image('logo.png', 10, 8, 56)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Histórico da Conversa', 0, 1, 'C')

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')

    def chapter_body(self, body):
        body = body.encode('latin-1', 'replace').decode('latin-1')
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

# 2. Configuração da API do OpenAI
chave = st.secrets["CHAVE_API"]
client = OpenAI(api_key=chave)

st.title("Chatbot - Assistente Especializado")

# 3. Inicialização da variável de saída do PDF e do contexto
pdf_output = 'historico_conversa.pdf'
if "contexto" not in st.session_state:
    st.session_state.contexto = ""

# 7. Função para verificar a moderação usando a API da OpenAI
def verificar_moderacao_openai(input_usuario):
    try:
        response = client.moderations.create(input=input_usuario)
        df = pd.DataFrame(dict(response.results[0].category_scores).items(), columns=['Category', 'Value'])
        maior_valor = df.sort_values(by='Value', ascending=False).iloc[0]

        if maior_valor['Value'] > st.session_state.limiar_moderacao:
            return "Sua mensagem pode conter conteúdo inapropriado. Por favor, modifique sua mensagem."
    except Exception as e:
        print(f"Erro na moderação: {e}")
    return None


# 8. Iniciar ou continuar histórico do chat
if st.session_state.especialidade and "mensagens" in st.session_state:
    for mensagem in st.session_state.mensagens:
        with st.chat_message(mensagem["role"]):
            st.markdown(mensagem["content"])

    prompt = st.chat_input("Digite sua pergunta")

    if prompt:
        resposta_moderacao = verificar_moderacao_openai(prompt)
        if resposta_moderacao:
            with st.chat_message("system"):
                st.markdown(resposta_moderacao)
        else:
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.mensagens.append({"role": "user", "content": prompt})

            mensagens_para_api = [
                {"role": "system", "content": st.session_state.contexto}] if st.session_state.contexto else []
            mensagens_para_api += st.session_state.mensagens

            resposta = client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=mensagens_para_api
            ).choices[0].message.content

            with st.chat_message("system"):
                st.markdown(resposta)
            st.session_state.mensagens.append({"role": "system", "content": resposta})

# 9. Botão para finalizar a conversa e gerar o PDF
if "mensagens" in st.session_state and st.session_state.mensagens and st.button('Finalizar Conversa'):
    df = pd.DataFrame(st.session_state.mensagens)
    if 'content' in df:
        df['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df['tokens'] = df['content'].apply(lambda x: len(x.split()))
        total_tokens = df['tokens'].sum()
        custo_por_token = 0.0001
        custo_estimado = total_tokens * custo_por_token
        df['custo_estimado'] = custo_estimado

        pdf = PDF()
        pdf.add_page()

        pdf.chapter_title('Informações da Conversa')
        info_str = f"Dia e Horário: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        info_str += f"Tokens Utilizados: {total_tokens}\n"
        info_str += f"Custo Estimado: {custo_estimado}\n"
        pdf.chapter_body(info_str)

        pdf.chapter_title('Histórico do Diálogo')
        for index, row in df.iterrows():
            role = "P: " if row["role"] == "user" else "R: "
            text = role + row['content']
            pdf.chapter_body(text)

        pdf.output(pdf_output)

        st.session_state.reset = True
        st.rerun()

# 10. Exibir botões de download do PDF e de reiniciar a conversa
if "reset" in st.session_state and st.session_state.reset:
    with open(pdf_output, "rb") as file:
        st.download_button(
            label="Download PDF",
            data=file,
            file_name="historico_conversa.pdf",
            mime="application/octet-stream"
        )

    if st.button("Zerar Conversa"):
        st.session_state.clear()
        st.session_state.especialidade = ""
        st.experimental_rerun()
