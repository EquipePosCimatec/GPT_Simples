import streamlit as st

#cabeçalho

col1,_, col2, __ = st.columns([3,2,3,2])

# Posicionando as imagens em cada coluna
with col1:
          st.image('https://www.mpba.mp.br/sites/all/themes/prodeb/logo.png', width=300)
with col2:
          st.image('https://arquivo.rhsconsult.com.br/logo/1695063140_senai%20cimatec.png', width=300)
st.markdown("---")

# Título
st.title('Aplicação de Data Science e Analytics')

# Introdução
st.markdown("""Este trabalho tem como objetivo explorar a aplicação de Data Science e Analytics, para contrução do TCC, com base no aprendizado da Pós Graduação do MPBA no Cimatec. Através do uso de técnicas implementadas na linguagem Python, inteligência Artificial, RAG e LLM os 
**Servidores Carlos Stucki, Gerson Yamashita e Sandro Dantas**
 fezeram um aplicativo protótipo para demonstração, com a funcionalidade de produção de artefatos de licitação.""")

# Modelos de Machine Learning
st.subheader('Funcionalidades do aplicativo:')

# Modelos dos Artefatos
st.markdown("""
**Modelos dos Artefatos:**
O usuário poderá carregar os modelos dos artefatos que serão utilizados no aplicativo.""")

# Documentos relevantes
st.markdown("""
**Inserir documentos relevantes:**
O usuário poderá carregar os documentos relevantes para a construção dos artefatos no aplicativo.""")

# Geração dos artefatos
st.markdown("""
**Geração dos artefatos de licitação:**
Com base nos modelos e documentos carregados, o aplicativo vai gerar os artefatos escolhidos.""")


# Link das páginas onde o texto foi identificado
#st.markdown("""
#**Link das páginas onde o texto foi identificado:**
#O aplicativo trás de forma imediata o link para acesso direto das páginas do Diário Oficial que o texto procurado foi identificado, referente as publicações do MPBA, em determinada data.""")
