import streamlit as st
import pandas as pd
import json
import os
import tempfile
import base64
from streamlit_agraph import agraph, Node, Edge, Config
from kg_extractor import KnowledgeGraphExtractor
from utils import get_color_by_entity_type

# 페이지 설정
st.set_page_config(
    page_title="한국어 지식 그래프 생성기",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        text-align: center;
        font-size: 2.5rem;
        color: #1E3A8A;
        margin-bottom: 0;
    }
    .sub-header {
        text-align: center;
        font-size: 1.2rem;
        color: #6B7280;
        margin-top: 0;
    }
    .stButton button {
        width: 100%;
    }
    .entity-label {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 4px;
        margin-right: 5px;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #6B7280;
        font-size: 0.8rem;
    }
    /* 카드 효과 */
    .css-1r6slb0 {
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'graph_data' not in st.session_state:
    st.session_state.graph_data = None
if 'entities_df' not in st.session_state:
    st.session_state.entities_df = None
if 'relations_df' not in st.session_state:
    st.session_state.relations_df = None
if 'relations_with_info_df' not in st.session_state:
    st.session_state.relations_with_info_df = None
if 'jsonl_content' not in st.session_state:
    st.session_state.jsonl_content = None

# 샘플 텍스트
sample_text = """
서울 강남구에서 열린 기술 컨퍼런스에서 김민수 교수가 인공지능의 미래에 대한 강연을 했다. 
이번 행사는 삼성전자와 네이버가 공동 주최했으며, 약 500명의 전문가들이 참석했다. 
김민수 교수는 서울대학교 컴퓨터공학과 소속으로, 인공지능 발전의 윤리적 측면을 강조했다. 
네이버의 이기획 부사장은 회사의 새로운 AI 서비스를 소개했으며, 삼성전자의 정기술 상무가 반도체 기술과 AI의 연관성에 대해 발표했다. 
행사 후 김민수 교수와 이기획 부사장은 한국 AI 산업의 발전 방향에 대해 토론했다. 
토론 중 서울대학교와 네이버의 산학협력 가능성도 언급되었다. 
한편, 정부 측에서는 과학기술정보통신부 안장관이 참석하여 인공지능 산업 지원 정책을 발표했다. 
안장관은 김민수 교수와 삼성전자의 연구 프로젝트에 정부 지원을 약속했다. 
이 행사는 대한민국 AI 기술 발전에 중요한 이정표가 될 것으로 전문가들은 평가했다.
"""

# 타이틀
st.markdown('<h1 class="main-header">한국어 지식 그래프 생성기</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">텍스트를 입력하면 개체(Entity)와 관계(Relation)를 추출하여 그래프로 시각화합니다.</p>', unsafe_allow_html=True)

# 사이드바
with st.sidebar:
    st.title("⚙️ 설정")
    
    # API 키 입력
    api_key = st.text_input("Gemini API 키", type="password", help="Google AI Studio에서 발급받은 API 키를 입력하세요.")
    
    # API 키 저장
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    
    # Gemini 모델 설정
    st.subheader("모델 설정")
    model_name = st.selectbox(
        "Gemini 모델",
        ["models/gemini-2.0-pro-exp-02-05", "models/gemini-1.5-pro"]
    )
    
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1, 
                            help="값이 낮을수록 일관된 결과, 높을수록 다양한 결과가 생성됩니다.")
    
    # 개체 유형 색상 표시
    st.subheader("개체 유형")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f'<div class="entity-label" style="background-color: {get_color_by_entity_type("PERSON")}">인물</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="entity-label" style="background-color: {get_color_by_entity_type("ORGANIZATION")}">조직</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="entity-label" style="background-color: {get_color_by_entity_type("LOCATION")}">장소</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f'<div class="entity-label" style="background-color: {get_color_by_entity_type("EVENT")}">이벤트</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="entity-label" style="background-color: {get_color_by_entity_type("PRODUCT")}">제품</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="entity-label" style="background-color: {get_color_by_entity_type("OTHER")}">기타</div>', unsafe_allow_html=True)
    
    # 저작권 정보
    st.sidebar.markdown("""
    <div class="footer">
        © 2025 한국어 지식 그래프 생성기<br>
        <a href="https://github.com/your-username/korean-knowledge-graph-streamlit" target="_blank">GitHub</a>
    </div>
    """, unsafe_allow_html=True)

# 메인 컨텐츠
tab1, tab2, tab3 = st.tabs(["📝 텍스트 입력", "📊 데이터 보기", "📥 내보내기"])

with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 텍스트 입력 영역
        text_input = st.text_area(
            "분석할 텍스트를 입력하세요",
            height=300,
            placeholder="여기에 한국어 텍스트를 입력하세요..."
        )
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # 샘플 텍스트 불러오기
        if st.button("샘플 텍스트 불러오기", use_container_width=True):
            text_input = sample_text
            st.session_state.text_input = sample_text
            st.experimental_rerun()
        
        # 입력 지우기
        if st.button("입력 지우기", use_container_width=True):
            text_input = ""
            st.session_state.text_input = ""
            st.experimental_rerun()
    
    # 분석 버튼
    if st.button("분석하기", type="primary", use_container_width=True):
        if not text_input:
            st.error("텍스트를 입력해주세요.")
        elif not api_key and not os.environ.get("GOOGLE_API_KEY"):
            st.error("Gemini API 키를 입력해주세요.")
        else:
            with st.spinner("지식 그래프를 생성하는 중입니다..."):
                try:
                    # 임시 디렉토리 생성
                    temp_dir = tempfile.mkdtemp()
                    
                    # 지식 그래프 추출
                    extractor = KnowledgeGraphExtractor(
                        api_key=api_key,
                        model_name=model_name,
                        temperature=temperature,
                        output_dir=temp_dir
                    )
                    
                    result = extractor.extract(text_input)
                    
                    if result["success"]:
                        # 세션 상태에 결과 저장
                        st.session_state.graph_data = result["data"]
                        st.session_state.entities_df = result["dataframes"]["entities"]
                        st.session_state.relations_df = result["dataframes"]["relations"]
                        
                        if "relations_with_info" in result["dataframes"]:
                            st.session_state.relations_with_info_df = result["dataframes"]["relations_with_info"]
                        
                        # JSONL 파일 읽기
                        with open(result["jsonl_path"], 'r', encoding='utf-8') as f:
                            st.session_state.jsonl_content = f.read()
                            
                        # 성공 메시지
                        n_entities = len(result["data"]["entities"])
                        n_relations = len(result["data"]["relations"])
                        
                        st.success(f"지식 그래프 추출 성공! 개체 {n_entities}개, 관계 {n_relations}개를 찾았습니다.")
                        
                        # 그래프 시각화 탭으로 전환
                        st.balloons()
                    else:
                        st.error(f"추출 실패: {result['message']}")
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")
    
    # 그래프 표시
    if st.session_state.graph_data:
        st.subheader("지식 그래프 시각화")
        
        # 노드 및 엣지 생성
        nodes = []
        edges = []
        
        # 노드 생성
        for entity in st.session_state.graph_data["entities"]:
            nodes.append(
                Node(
                    id=entity["id"],
                    label=entity["name"],
                    color=get_color_by_entity_type(entity["type"]),
                    size=25,
                    title=f"유형: {entity['type']}<br>설명: {entity['description']}"
                )
            )
        
        # 엣지 생성
        for relation in st.session_state.graph_data["relations"]:
            edges.append(
                Edge(
                    source=relation["source"],
                    target=relation["target"],
                    label=relation["relation"],
                    title=relation.get("sentence", "")
                )
            )
        
        # 그래프 설정
        config = Config(
            width="100%",
            height=600,
            directed=True,
            physics=True,
            hierarchical=False,
            node={
                "shape": "circle",
                "font": {"size": 14, "face": "Nanum Gothic"},
                "scaling": {"min": 20, "max": 40},
                "shadow": True
            },
            edge={
                "font": {"size": 12, "face": "Nanum Gothic"},
                "smooth": {"type": "dynamic"},
                "arrows": {"to": {"enabled": True, "scaleFactor": 0.5}}
            },
            interaction={
                "hover": True,
                "navigationButtons": True,
                "keyboard": True,
                "tooltipDelay": 300
            }
        )
        
        # 그래프 렌더링
        agraph(nodes=nodes, edges=edges, config=config)

with tab2:
    if st.session_state.graph_data:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("개체 (Entities)")
            st.dataframe(st.session_state.entities_df, use_container_width=True)
        
        with col2:
            st.subheader("관계 (Relations)")
            st.dataframe(st.session_state.relations_df, use_container_width=True)
        
        if st.session_state.relations_with_info_df is not None:
            st.subheader("관계 정보 (Relations with Info)")
            st.dataframe(st.session_state.relations_with_info_df, use_container_width=True)
    else:
        st.info("먼저 텍스트를 분석해주세요.")

with tab3:
    if st.session_state.graph_data:
        st.subheader("데이터 내보내기")
        
        # CSV 다운로드 버튼
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.session_state.entities_df is not None:
                entities_csv = st.session_state.entities_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="개체 CSV 다운로드",
                    data=entities_csv,
                    file_name="entities.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col2:
            if st.session_state.relations_df is not None:
                relations_csv = st.session_state.relations_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="관계 CSV 다운로드",
                    data=relations_csv,
                    file_name="relations.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with col3:
            if st.session_state.relations_with_info_df is not None:
                relations_info_csv = st.session_state.relations_with_info_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button(
                    label="관계정보 CSV 다운로드",
                    data=relations_info_csv,
                    file_name="relations_with_info.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        # JSONL 다운로드 버튼
        if st.session_state.jsonl_content:
            st.download_button(
                label="JSONL 파일 다운로드",
                data=st.session_state.jsonl_content.encode('utf-8'),
                file_name="extracted_data.jsonl",
                mime="application/jsonl",
                use_container_width=True
            )
        
        # JSON 다운로드 버튼
        json_data = json.dumps(st.session_state.graph_data, ensure_ascii=False, indent=2).encode('utf-8')
        st.download_button(
            label="JSON 파일 다운로드",
            data=json_data,
            file_name="knowledge_graph.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.info("먼저 텍스트를 분석해주세요.")
