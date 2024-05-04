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

# Quantidade de Páginas
st.markdown("""
**Modelos dos Artefatos:**
#O aplicativo trás de forma imediata a quantidade de páginas do Diário Oficial, referente as publicações do MPBA, em determinada data.""")

# Quantidade de vezes que o texto procurado foi identificado no Diário Oficial
st.markdown("""
**Inserir documentos relevantes:**
#O aplicativo trás de forma imediata a quantidade de vezes que o texto procurado foi identificado no Diário Oficial, referente as publicações do MPBA, em determinada data.""")

# As páginas do Diário Oficial que o texto foi identificado
st.markdown("""
**Geração dos artefatos de licitação:**
#O aplicativo trás de forma imediata as páginas do Diário Oficial que o texto procurado foi identificado, referente as publicações do MPBA, em determinada data.""")


# Link das páginas onde o texto foi identificado
#st.markdown("""
#**Link das páginas onde o texto foi identificado:**
#O aplicativo trás de forma imediata o link para acesso direto das páginas do Diário Oficial que o texto procurado foi identificado, referente as publicações do MPBA, em determinada data.""")
