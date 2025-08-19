# ----------------------------------------------------------------
# MAIN APP WITH MULTI-PAGE NAVIGATION
# ----------------------------------------------------------------
import streamlit as st
import pandas as pd
import json
import keplergl
import os
from databricks import sql
from databricks.sdk.core import Config
from streamlit_keplergl import keplergl_static
import h3
import pydeck as pdk

# ----------------------------------------------------------------
# PAGE CONFIGURATION
# ----------------------------------------------------------------

st.set_page_config(
    page_title="Mapa de Inadimplência",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------------------------------------------------------
# SIDEBAR NAVIGATION
# ----------------------------------------------------------------

# Logo
st.sidebar.image(
    "https://raw.githubusercontent.com/Databricks-BR/lab_agosto_2025/refs/heads/main/images/app_logo.png", 
    width=200
)

st.sidebar.header("Mapa de Inadimplência")

# PAGE SELECTION
page = st.sidebar.selectbox(
    "Escolha uma página:",
    ["🗺️ Mapa Interativo", "🗺️ Mapa Interativo 3D", "🤖 Chat com Genie", "📊 Dashboard", "ℹ️ Sobre"]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Links Úteis")
st.sidebar.link_button("Repositório Git", "https://github.com/Databricks-BR/lab_agosto_2025")
st.sidebar.link_button("Referências", "https://github.com/Databricks-BR/lab_agosto_2025/blob/main/README.md#refer%C3%AAncias-adicionais")
st.sidebar.link_button("Contato", "mailto:amazonia.geoai@databricks.com")

# ----------------------------------------------------------------
# HEADER IMAGE
# ----------------------------------------------------------------

st.image(
    "https://raw.githubusercontent.com/Databricks-BR/lab_agosto_2025/refs/heads/main/images/head_lab.png",
    use_column_width=True
)

# ----------------------------------------------------------------
# DATABASE CONNECTION (SHARED)
# ----------------------------------------------------------------

assert os.getenv('DATABRICKS_WAREHOUSE_ID'), "DATABRICKS_WAREHOUSE_ID must be set in app.yaml."

def sqlQuery(query: str) -> pd.DataFrame:
    cfg = Config()
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        credentials_provider=lambda: cfg.authenticate
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall_arrow().to_pandas()

@st.cache_data(ttl=30)
def getData():
     # Insira o nome da tabela criada
    return sqlQuery("select * from academy.genie_aibi.gold_faturamento_h3")

# ----------------------------------------------------------------
# PAGE ROUTING
# ----------------------------------------------------------------

if page == "🗺️ Mapa Interativo":
    # ----------------------------------------------------------------
    # MAP PAGE - SIMPLE 2D HEATMAP WITH KEPLER.GL
    # ----------------------------------------------------------------
    
    st.subheader("🗺️ Monitoramento das áreas de inadimplência")
    
    try:
        df = getData()
        if 'contagem_clientes' in df.columns:
            total_clientes = int(df['contagem_clientes'].sum())
            st.success(f"Total de clientes inadimplentes: {total_clientes:,}")
    except Exception as e:
        st.error(f"Erro carregando os dados: {e}")
        st.stop()
    
    if df.empty:
        st.error("Nenhum dado encontrado!")
        st.stop()
    
    # --- Data Processing ---
    h3_column = next((col for col in df.columns if 'h3' in col.lower()), None)
    if not h3_column:
        st.error("Nenhuma coluna H3 encontrada!")
        st.stop()
    
    def convert_h3_simple(x):
        if pd.isna(x): return None
        try:
            return format(int(x), '0>15x') if isinstance(x, (int, float)) else str(x)
        except (ValueError, TypeError):
            return None

    # Include all required columns in the DataFrame
    final_df = df.copy()
    final_df['h3'] = final_df[h3_column].apply(convert_h3_simple)
    final_df["contagem_clientes"] = pd.to_numeric(final_df.get("contagem_clientes"), errors="coerce")
    
    # Ensure all necessary columns exist and are clean
    required_cols = ['h3', 'contagem_clientes', 'genero_cliente', 'bairro', 'faixa_divida']
    final_df.dropna(subset=required_cols, inplace=True)
    
    # --- Kepler Configuration ---
    kepler_config = {
        "version": "v1",
        "config": {
            "visState": {
                "layers": [{
                    "id": "inadimplencia_h3_layer",
                    "type": "h3",
                    "config": {
                        "dataId": "inadimplencia_data",
                        "label": "Inadimplência por Contagem",
                        "columns": {"hex_id": "h3"},
                        "isVisible": True,
                        "visConfig": {
                            "opacity": 0.8,
                            "colorRange": {
                                "name": "Global Warming",
                                "type": "sequential",
                                "category": "Uber",
                                "colors": ['#FFC300', '#F1920E', '#E3611C', '#C70039', '#900C3F', '#5A1846']
                            },
                            "coverage": 0.9,
                            "filled": True,
                            "enable3d": False
                        },
                        "colorField": {
                            "name": "contagem_clientes",
                            "type": "integer"
                        },
                        "colorAggregation": "sum"
                    }
                }],
                "interactionConfig": {
                    "tooltip": {
                        "fieldsToShow": {
                            "inadimplencia_data": [
                                {"name": "contagem_clientes", "format": None},
                                {"name": "bairro", "format": None}
                            ]
                        },
                        "enabled": True
                    }
                }
            },
            "mapState": {
                "latitude": -23.65,
                "longitude": -46.65,
                "zoom": 11,
                "pitch": 0,
                "bearing": 0
            }
        }
    }

    # --- Display Map ---
    try:
        map_1 = keplergl.KeplerGl(height=600, config=kepler_config)
        # CHANGE: Pass the full DataFrame with all columns to the map
        map_1.add_data(data=final_df, name="inadimplencia_data")
        
        map_html = map_1._repr_html_()
        st.components.v1.html(map_html, height=600)

    except Exception as e:
        st.error(f"Erro exibindo o mapa: {e}")


if page == "🗺️ Mapa Interativo 3D":
    # ----------------------------------------------------------------
    # MAP PAGE WITH PYDECK AND INTERACTIVE FILTERS
    # ----------------------------------------------------------------
    
    st.subheader("🗺️ Mapa Interativo de Inadimplência")
    
    try:
        df = getData()
        if 'contagem_clientes' in df.columns:
            total_clientes = int(df['contagem_clientes'].sum())
            st.success(f"Total de clientes inadimplentes: {total_clientes:,}")

    except Exception as e:
        st.error(f"Erro carregando os dados: {e}")
        st.stop()
    
    if df.empty:
        st.warning("Nenhum dado encontrado para exibir.")
        st.stop()
    
    # --- Data Processing ---
    h3_column = next((col for col in df.columns if 'h3' in col.lower()), None)
    if not h3_column:
        st.error("Nenhuma coluna H3 encontrada no DataFrame!")
        st.stop()

    def convert_h3_simple(x):
        if pd.isna(x): return None
        try:
            return format(int(x), '0>15x') if isinstance(x, (int, float)) else str(x)
        except (ValueError, TypeError):
            return None

    final_df = df.copy()
    final_df['h3'] = final_df[h3_column].apply(convert_h3_simple)
    for col in ['contagem_clientes', 'valor_inadimplencia', 'genero_cliente', 'bairro', 'faixa_divida']:
        if col in final_df.columns:
            if col in ['contagem_clientes', 'valor_inadimplencia']:
                 final_df[col] = pd.to_numeric(final_df[col], errors="coerce")
        else:
            st.error(f"Coluna necessária '{col}' não encontrada no DataFrame.")
            st.stop()
            
    final_df.dropna(subset=['h3', 'contagem_clientes', 'valor_inadimplencia'], inplace=True)
    
    st.markdown("---")

    # --- 1. Filter Controls (with no default selection) ---
    st.write("### Filtros")
    col1, col2, col3 = st.columns(3)

    with col1:
        unique_genders = sorted(final_df['genero_cliente'].unique())
        selected_genders = st.multiselect(
            "Selecione o Gênero:",
            options=unique_genders,
        )

    with col2:
        unique_bairros = sorted(final_df['bairro'].unique())
        selected_bairros = st.multiselect(
            "Selecione o Bairro:",
            options=unique_bairros,
        )

    with col3:
        unique_faixas = sorted(final_df['faixa_divida'].unique())
        selected_faixas = st.multiselect(
            "Selecione a Faixa de Dívida:",
            options=unique_faixas,
        )
    
    # --- 2. Apply Filters to the DataFrame ---
    filtered_df = final_df
    if selected_genders:
        filtered_df = filtered_df[filtered_df['genero_cliente'].isin(selected_genders)]
    if selected_bairros:
        filtered_df = filtered_df[filtered_df['bairro'].isin(selected_bairros)]
    if selected_faixas:
        filtered_df = filtered_df[filtered_df['faixa_divida'].isin(selected_faixas)]

    if filtered_df.empty:
        st.warning("Nenhum dado corresponde aos filtros selecionados. Por favor, ajuste sua seleção.")
        st.stop()

    # --- 3. Pydeck Configuration (uses 'filtered_df') ---
    view_state = pdk.ViewState(
        latitude=-23.65, longitude=-46.65, zoom=9, pitch=50, bearing=0
    )

    max_contagem = filtered_df['contagem_clientes'].max()
    if max_contagem == 0: max_contagem = 1

    h3_layer = pdk.Layer(
        "H3HexagonLayer",
        data=filtered_df,
        get_hexagon="h3",
        get_fill_color=f"[255, 255 * (1 - contagem_clientes / {max_contagem}), 0, 180]",
        get_elevation="valor_inadimplencia",
        extruded=True,
        elevation_scale=0.1,
        pickable=True,
        auto_highlight=True,
    )

    tooltip = {
       "html": """
            <b>Contagem de Clientes:</b> {contagem_clientes} <br/>
            <b>Valor da Inadimplência:</b> {valor_inadimplencia} <br/>
            <b>Bairro:</b> {bairro} <br/>
            <b>Gênero:</b> {genero_cliente}
            """,
       "style": {"backgroundColor": "steelblue", "color": "white"}
    }

    # --- 4. Render the map in Streamlit ---
    try:
        st.pydeck_chart(pdk.Deck(
            layers=[h3_layer],
            initial_view_state=view_state,
            map_style=pdk.map_styles.LIGHT,
            tooltip=tooltip
        ))
    except Exception as e:
        st.error(f"Ocorreu um erro ao renderizar o mapa com Pydeck: {e}")


elif page == "🤖 Chat com Genie":
    # ----------------------------------------------------------------
    # GENIE CHAT PAGE
    # ----------------------------------------------------------------
    import json
    from databricks.sdk import WorkspaceClient
    from databricks.sdk.service.dashboards import GenieAPI

    # Insira o ID do Genie Space criado anteriormente
    genie_space_id = "<INSIRA-AQUI-O-ID-DO-GENIE-SPACE>"

    workspace_client = WorkspaceClient(
        host=os.environ.get("DATABRICKS_HOST"),
        client_id=os.environ.get("DATABRICKS_CLIENT_ID"),
        client_secret=os.environ.get("DATABRICKS_CLIENT_SECRET"),
    )
    genie_api = GenieAPI(workspace_client.api_client)
    conversation_id = st.session_state.get("genie_conversation_id", None)

    def ask_genie_sync(question: str, space_id: str, conversation_id: str = None):
        import asyncio
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if conversation_id is None:
                initial_message = loop.run_until_complete(
                    loop.run_in_executor(None, genie_api.start_conversation_and_wait, space_id, question)
                )
                conversation_id_local = initial_message.conversation_id
            else:
                initial_message = loop.run_until_complete(
                    loop.run_in_executor(None, genie_api.create_message_and_wait, space_id, conversation_id, question)
                )
                conversation_id_local = conversation_id
            
            answer_json = {"message": ""}
            # Possible text attachment
            for attachment in initial_message.attachments:
                if getattr(attachment, "text", None) and getattr(attachment.text, "content", None):
                    answer_json["message"] = attachment.text.content
                    break
                if getattr(attachment, "query", None):
                    # Attempt to retrieve and display query & results
                    query_result = loop.run_until_complete(
                        loop.run_in_executor(None, genie_api.get_message_query_result,
                            space_id, initial_message.conversation_id, initial_message.id)
                    ) if hasattr(genie_api, "get_message_query_result") else None
                    # Get actual SQL result if present
                    if query_result and hasattr(query_result, "statement_response") and query_result.statement_response:
                        sql_results = loop.run_until_complete(
                            loop.run_in_executor(None, workspace_client.statement_execution.get_statement,
                                query_result.statement_response.statement_id)
                        )
                        answer_json["columns"] = sql_results.manifest.schema.as_dict()
                        answer_json["data"] = sql_results.result.as_dict()
                        desc = getattr(attachment.query, "description", "")
                        answer_json["query_description"] = desc
                        answer_json["sql"] = getattr(attachment.query, "query", "")
                        break
            loop.close()
            return answer_json, conversation_id_local
        except Exception as e:
            return {"message": f"Erro consultando Genie: {str(e)}"}, conversation_id
    
    def process_query_results(answer_json):
        response_blocks = []
        if "query_description" in answer_json and answer_json["query_description"]:
            response_blocks.append(f"**Descrição da Consulta:** {answer_json['query_description']}")
        if "sql" in answer_json:
            with st.expander("SQL gerado pelo Genie"):
                st.code(answer_json["sql"], language="sql")
        if "columns" in answer_json and "data" in answer_json:
            columns = answer_json["columns"]
            data = answer_json["data"]
            # Safe check for correct structure
            if isinstance(columns, dict) and "columns" in columns:
                # Render Pandas DataFrame in Streamlit
                col_names = [col["name"] for col in columns["columns"]]
                df = pd.DataFrame(data["data_array"], columns=col_names)
                st.markdown("**Resultados da Consulta:**")
                st.dataframe(df)
        elif "message" in answer_json:
            st.markdown(answer_json["message"])
        else:
            st.info("Sem resultados retornados.")
        for block in response_blocks:
            st.markdown(block)

    st.subheader("🤖 Genie: IA para consulta dos dados")
    st.markdown("Pergunte o que quiser sobre o dataset de inadimplência e obtenha insights em linguagem natural!")

    user_input = st.chat_input("Faça uma pergunta para Genie...")

    if user_input:
        st.chat_message("user").markdown(user_input)
        # Call Genie API and display response
        with st.chat_message("assistant"):
            with st.spinner("Consultando Genie..."):
                answer_json, new_conversation_id = ask_genie_sync(user_input, genie_space_id, conversation_id)
                st.session_state["genie_conversation_id"] = new_conversation_id
                process_query_results(answer_json)


elif page == "📊 Dashboard":
    # ----------------------------------------------------------------
    # ANALYTICS PAGE
    # ----------------------------------------------------------------
    
    st.markdown("---")
    st.subheader("⚡ Dashboard Interativo: Databricks AI/BI")

    # Insira o link do Embed Dashboard
    src_dashboard="<INSIRA-AQUI-O-LINK-DO-EMBED-DASHBOARD>"

    st.components.v1.iframe(
        src=src_dashboard,
        scrolling=True,
        height=600
    )


elif page == "ℹ️ Sobre":
    # ----------------------------------------------------------------
    # ABOUT PAGE
    # ----------------------------------------------------------------
    
    st.subheader("ℹ️ Sobre o Projeto")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## 🎯 Objetivo
        
        Este aplicativo fornece uma **visualização interativa da inadimplência** no estado de São Paulo, 
        utilizando dados geoespaciais e inteligência artificial para análises avançadas.
        
        ## 🛠️ Tecnologias Utilizadas
        
        - **Streamlit**: Interface web interativa e responsiva
        - **Kepler.gl** e **PyDeck**: Visualização geoespacial avançada com suporte a hexágonos H3
        - **Databricks**: Plataforma de dados, analytics e machine learning
        - **Genie Space**: Assistente de IA para consultas em linguagem natural
        - **H3**: Sistema de indexação hexagonal da Uber para análise geoespacial
        - **Python**: Para processamento dos dados
        
        ## 📊 Dados
        
        - **Escopo**: Estado de São Paulo
        - **Resolução**: Hexágonos H3 (resolução 09) para precisão otimizada
        - **Métricas**: Contagem de clientes inadimplentes por região
        - **Atualização**: Dados atualizados automaticamente via pipeline
        - **Fonte**: Sistema interno de gestão de clientes
        """)
    
    with col2:
        st.markdown("""
        ### 📈 Estatísticas do Sistema
        
        - **Hexágonos H3**: Resolução 09
        - **Área Coberta**: Estado de SP
        - **Atualizações**: Batch ou Tempo real
        - **Precisão**: Dados validados
        
        ### 🔧 Recursos Técnicos
        
        - **Performance**: Cache inteligente
        - **Segurança**: Conexão segura
        - **Escalabilidade**: Arquitetura na nuvem
        - **Disponibilidade**: 24/7
        """)
    
    st.markdown("---")
    
    st.markdown("""
    ## 🗺️ Funcionalidades
    
    ### 🗺️ Mapa Interativo
    - **Heatmap de inadimplência**: Visualização em tempo real das concentrações
    - **Navegação intuitiva**: Zoom e filtros interativos
    - **Sobreposições geográficas**: Camadas de contexto geográfico
    - **Detalhes por região**: Informações detalhadas ao clicar
    
    ### 🤖 Chat com IA (Genie)
    - **Perguntas em linguagem natural**: "Qual região tem mais inadimplentes?"
    - **Análises automáticas**: Insights gerados pela IA
    - **Consultas predefinidas**: Templates para análises comuns
    - **Integração completa**: Acesso direto aos dados do sistema
    
    ### 📊 Dashboard de Análises
    - **Métricas em tempo real**: KPIs principais sempre atualizados
    - **Visualizações interativas**: Gráficos e tabelas dinâmicas
    - **Rankings e comparações**: Top regiões e análises comparativas
    - **Análise estatística**: Quartis, médias, distribuições
    
    ## 🚀 Como Usar
    
    1. **📊 Visualize** os dados no mapa interativo
    2. **🤖 Faça perguntas** para o assistente Genie
    3. **📈 Analise** métricas e estatísticas detalhadas
    4. **💡 Obtenha insights** para tomada de decisão
    
    ## 🎨 Tecnologia de Ponta
    
    Este aplicativo representa a união entre **visualização de dados moderna**, 
    **inteligência artificial conversacional** e **análise geoespacial avançada**, 
    proporcionando uma experiência única para análise de inadimplência.
    """)
    
    st.markdown("---")
    
    # Footer
    col_footer1, col_footer2, col_footer3 = st.columns(3)
    
    with col_footer1:
        st.markdown("""
        **🏢 Databricks Brasil**
        - Plataforma de dados unificada
        - Analytics e IA democratizados
        - Inovação em cada projeto
        """)
    
    with col_footer2:
        st.markdown("""
        **🔗 Links Úteis**
        - [Documentação Técnica](https://github.com/Databricks-BR/lab_agosto_2025)
        - [Suporte e Dúvidas](https://www.databricks.com/br)
        - [Contato](mailto:amazonia.geoai@databricks.com)
        """)
    
    with col_footer3:
        st.markdown("""
        **📄 Versão**
        - App: v1.0.0
        - Última atualização: Ago/2025
        - Status: ✅ Ativo
        """)
    
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 20px; background: linear-gradient(90deg, #FF6B35, #F7931E); border-radius: 10px; color: white;'>
        <h3>🚀 Desenvolvido pela equipe Databricks Brasil</h3>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------------------------------------------
# FOOTER
# ----------------------------------------------------------------

if page != "🤖 Chat com Genie":
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; font-size: 12px; padding: 10px;'>
        © 2025 Databricks Brasil - Mapa de Inadimplência | Powered by Streamlit, Kepler.gl, PyDeck & Databricks
    </div>
    """, unsafe_allow_html=True)



