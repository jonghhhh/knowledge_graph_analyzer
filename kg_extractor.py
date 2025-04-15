import os
import json
import re
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any

class KnowledgeGraphExtractor:
    """지식 그래프 데이터 추출기 
    - Gemini 기반으로 개체(엔티티)와 관계를 추출하여 JSONL과 CSV 파일(entities, relations, relations_with_info)을 생성합니다.
    """
    
    def __init__(self, api_key=None, model_name="models/gemini-2.0-pro-exp-02-05", temperature=0.2, output_dir="./output"):
        """
        초기화 함수
        
        매개변수:
            api_key (str): Google API 키 (없으면 환경 변수에서 가져옴)
            model_name (str): 사용할 Gemini 모델명
            temperature (float): 생성 다양성 조절 (0에 가까울수록 일관된 결과)
            output_dir (str): 결과 파일 저장 경로
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model_name = model_name
        self.temperature = temperature
        self.output_dir = output_dir
        
        # 출력 디렉토리 생성
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Gemini API 설정 (API 키가 반드시 필요)
        if not self.api_key:
            raise ValueError("Google API 키가 설정되어 있지 않습니다.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(
            model_name=self.model_name,
            generation_config={"temperature": self.temperature}
        )


    def extract(self, text, output_dir=None):
        """
        텍스트에서 지식그래프 데이터를 추출하고 저장
        
        매개변수:
            text (str): 분석할 텍스트
            output_dir (str): 결과 저장 경로 (없으면 기본 경로 사용)
            
        반환값:
            dict: 결과 데이터와 파일 경로 포함
        """
        output_dir = output_dir or self.output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Gemini API를 사용하여 개체 및 관계 추출
        data = self._extract_with_llm(text)
        
        if not data or not data.get("entities"):
            return {"success": False, "message": "개체 추출에 실패했습니다"}
        
        # JSONL 파일 저장
        jsonl_path = self._save_jsonl(data, output_dir)
        
        # 데이터프레임 생성
        dataframes = self._create_dataframes(data)
        
        # 데이터프레임 저장
        dataframe_paths = self._save_dataframes(dataframes, output_dir)
        
        return {
            "success": True, 
            "data": data,
            "jsonl_path": jsonl_path,
            "dataframe_paths": dataframe_paths,
            "dataframes": dataframes
        }
    
    def _extract_with_llm(self, text):
        """
        Gemini 모델을 사용하여 개체 및 관계 추출
        
        매개변수:
            text (str): 분석할 텍스트
            
        반환값:
            dict: 추출된 개체와 관계 정보
        """
        prompt = f"""
        당신은 한국어 텍스트에서 개체(엔티티)와 관계를 추출하는 전문가입니다.
        다음 텍스트에서 모든 중요한 개체(인물, 조직, 장소 등)와 그들 간의 관계를 추출해주세요.
        
        다음 규칙을 반드시 따라주세요:
        1. 개체는 명확한 고유명사(인물, 조직, 장소 등)만 추출하세요.
        2. 일반 명사, 동사, 형용사, 부사 등은 개체로 추출하지 마세요.
        3. 관계는 두 개체 간의 의미 있는 연결을 나타내야 합니다.
        4. 각 개체에는 고유 ID를 부여하고, 개체명, 유형, 설명을 포함해주세요.
        5. 각 관계에는 소스 개체 ID, 타겟 개체 ID, 관계 유형, 관련 문장을 포함해주세요.
        
        개체 유형은 다음과 같이 분류해주세요:
        - PERSON: 사람, 인물
        - ORGANIZATION: 회사, 정부, 기관, 단체 등
        - LOCATION: 국가, 도시, 지역 등
        - EVENT: 행사, 사건, 회의 등
        - PRODUCT: 제품, 서비스, 기술 등
        - OTHER: 기타 중요 개체
        
        다음 형식의 JSON으로 응답해주세요:
        ```json
        {{
            "entities": [
                {{
                    "id": "E1",
                    "name": "김민수",
                    "type": "PERSON",
                    "description": "서울대학교 컴퓨터공학과 교수"
                }},
                ...
            ],
            "relations": [
                {{
                    "source": "E1",
                    "target": "E2",
                    "relation": "소속",
                    "sentence": "김민수 교수는 서울대학교 컴퓨터공학과 소속이다."
                }},
                ...
            ]
        }}
        ```
        
        분석할 텍스트:
        ---
        {text}
        ---
        
        중요: 응답은 반드시 위에 명시된 JSON 형식만 포함해야 합니다. 다른 텍스트나 설명은 포함하지 마세요.
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # JSON 추출
            json_match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'({.*})', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response_text
            
            data = json.loads(json_str)
            
            if "entities" not in data:
                data["entities"] = []
            if "relations" not in data:
                data["relations"] = []
                
            return data
                
        except Exception as e:
            print(f"Gemini API 호출 중 오류 발생: {e}")
            return {"entities": [], "relations": []}
    
    def _save_jsonl(self, data: Dict[str, Any], output_dir: str) -> str:
        """
        데이터를 JSONL 형식으로 저장
        
        매개변수:
            data (dict): 저장할 데이터 (entities, relations 포함)
            output_dir (str): 저장 경로
            
        반환값:
            str: 생성된 JSONL 파일 경로
        """
        jsonl_path = os.path.join(output_dir, "extracted_data.jsonl")
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for entity in data.get("entities", []):
                f.write(json.dumps({"type": "entity", "data": entity}, ensure_ascii=False) + "\n")
            for relation in data.get("relations", []):
                f.write(json.dumps({"type": "relation", "data": relation}, ensure_ascii=False) + "\n")
        return jsonl_path
    
    def _create_dataframes(self, data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        pandas DataFrame 형식으로 변환
        
        매개변수:
            data (dict): 개체와 관계 정보
        
        반환값:
            dict: 'entities', 'relations', 'relations_with_info' DataFrame 사전.
        """
        # 개체 DataFrame
        entities = data.get("entities", [])
        entities_df = pd.DataFrame(entities).fillna("")
        if "description" not in entities_df.columns:
            entities_df["description"] = ""
        # 관계 DataFrame
        relations = data.get("relations", [])
        relations_df = pd.DataFrame(relations).fillna("")
        # 관계 정보에 개체 정보 병합
        if not relations_df.empty and not entities_df.empty:
            source_info = entities_df[["id", "name", "type"]].copy()
            source_info.columns = ["source", "source_name", "source_type"]
            merged_df = relations_df.merge(source_info, on="source", how="left")
            target_info = entities_df[["id", "name", "type"]].copy()
            target_info.columns = ["target", "target_name", "target_type"]
            merged_df = merged_df.merge(target_info, on="target", how="left")
            merged_df.rename(columns={"source": "source_id", "target": "target_id"}, inplace=True)
            rel_info_columns = ["source_id", "source_name", "source_type", "target_id", "target_name", "target_type", "relation", "sentence"]
            relations_with_info_df = merged_df[rel_info_columns]
        else:
            relations_with_info_df = pd.DataFrame(columns=["source_id", "source_name", "source_type", "target_id", "target_name", "target_type", "relation", "sentence"])
        return {
            "entities": entities_df,
            "relations": relations_df,
            "relations_with_info": relations_with_info_df
        }
    
    def _save_dataframes(self, dataframes: Dict[str, pd.DataFrame], output_dir: str) -> Dict[str, str]:
        """
        DataFrame을 CSV 파일로 저장
        
        매개변수:
            dataframes (dict): 저장할 DataFrame 사전 (entities, relations, relations_with_info)
            output_dir (str): 저장 경로
            
        반환값:
            dict: 저장된 파일 경로 사전
        """
        paths = {}
        if not dataframes["entities"].empty:
            entity_csv = os.path.join(output_dir, "entities.csv")
            dataframes["entities"].to_csv(entity_csv, index=False, encoding='utf-8-sig')
            paths["entities_csv"] = entity_csv
        if not dataframes["relations"].empty:
            relations_csv = os.path.join(output_dir, "relations.csv")
            dataframes["relations"].to_csv(relations_csv, index=False, encoding='utf-8-sig')
            paths["relations_csv"] = relations_csv
        if not dataframes["relations_with_info"].empty:
            rel_info_csv = os.path.join(output_dir, "relations_with_info.csv")
            dataframes["relations_with_info"].to_csv(rel_info_csv, index=False, encoding='utf-8-sig')
            paths["relations_with_info_csv"] = rel_info_csv
        return paths
    
    def _create_static_graph(self, G, output_file: str) -> str:
        """
        Matplotlib으로 정적 그래프 생성 (PNG)
        
        Args:
            G: NetworkX 지식그래프
            output_file (str): 저장할 이미지 파일 경로
        
        Returns:
            str: 생성된 이미지 파일 경로
        """
        if len(G) == 0:
            return ""
        
        import matplotlib.pyplot as plt
        plt.figure(figsize=(14, 12))
        
        color_map = {
            "PERSON": "skyblue",
            "ORGANIZATION": "lightgreen",
            "LOCATION": "salmon",
            "EVENT": "gold",
            "PRODUCT": "mediumpurple",
            "OTHER": "lightgray"
        }
        
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            node_type = G.nodes[node].get("type", "OTHER")
            node_colors.append(color_map.get(node_type, "lightgray"))
            node_size = 400 + (120 * G.degree[node])
            node_sizes.append(node_size)
        
        pos = nx.spring_layout(G, k=0.7, seed=42)
        nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color=node_colors, alpha=0.9, edgecolors='black', linewidths=1.0)
        nx.draw_networkx_edges(G, pos, width=1.5, alpha=0.8, edge_color='gray', arrowsize=20)
        
        labels = {node: G.nodes[node].get("name", node) for node in G.nodes()}
        for node, label in labels.items():
            x, y = pos[node]
            plt.text(x, y, label, fontsize=12, fontweight='bold', fontproperties=plt.rcParams['font.family'],
                     ha='center', va='center',
                     bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.3'))
        
        for u, v, data in G.edges(data=True):
            relation = data.get("relation", "")
            edge_x = (pos[u][0] + pos[v][0]) / 2.0
            edge_y = (pos[u][1] + pos[v][1]) / 2.0
            plt.text(edge_x, edge_y, relation, fontsize=10, fontweight='bold', fontproperties=plt.rcParams['font.family'],
                     ha='center', va='center',
                     bbox=dict(facecolor='white', alpha=0.8, edgecolor='gray', boxstyle='round,pad=0.2'))
        
        legend_elements = [ 
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=12, label=label)
            for label, color in color_map.items()
        ]
        plt.legend(handles=legend_elements, loc='upper right', title="개체 유형", fontsize=10, title_fontsize=12)
        plt.axis('off')
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        return output_file

    def _create_interactive_graph(self, G, output_file: str) -> str:
        """
        Pyvis로 인터랙티브 그래프 생성 (HTML)
        
        Args:
            G: NetworkX 지식그래프
            output_file (str): 저장할 HTML 파일 경로
        
        Returns:
            str: 생성된 HTML 파일 경로
        """
        if len(G) == 0:
            return ""
        
        from pyvis.network import Network
        net = Network(height="800px", width="100%", directed=True, notebook=False, bgcolor="#ffffff")
        net.set_options("""
        var options = {
          "nodes": {
            "font": {
              "size": 24,
              "face": "Nanum Gothic, Malgun Gothic, Apple Gothic, 맑은 고딕, 돋움, sans-serif",
              "bold": true
            }
          },
          "edges": {
            "font": {
              "size": 20,
              "face": "Nanum Gothic, Malgun Gothic, Apple Gothic, 맑은 고딕, 돋움, sans-serif",
              "bold": true
            }
          }
        }
        """)
        
        # 노드 추가
        for node_id in G.nodes():
            node_data = G.nodes[node_id]
            node_type = node_data.get("type", "OTHER")
            node_name = node_data.get("name", node_id)
            node_desc = node_data.get("description", "")
            title = f"<div style='font-size:16px;'><strong>{node_name}</strong><br>{node_desc}</div>"
            net.add_node(node_id, label=node_name, title=title, color=None)
        # 엣지 추가
        for u, v, data in G.edges(data=True):
            relation = data.get("relation", "")
            sentence = data.get("sentence", "")
            title = f"<div style='font-size:16px;'><strong>{relation}</strong><br>{sentence}</div>"
            net.add_edge(u, v, title=title, label=relation, arrows="to")
        
        net.save_graph(output_file)
        return output_file

# __main__ 블록: 샘플 텍스트를 사용하여 실행 예제 제공
if __name__ == "__main__":
    # API 키 확인
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("Google API 키가 환경 변수에 설정되어 있지 않습니다.")
        print("export GOOGLE_API_KEY='your-api-key-here' 명령으로 설정하세요.")
        exit(1)
    
    # 샘플 텍스트 불러오기: sample_news.txt 파일이 있을 경우 읽고, 없으면 기본 텍스트 사용
    sample_file = os.path.join(os.getcwd(), "sample_news.txt")
    if os.path.exists(sample_file):
        with open(sample_file, "r", encoding="utf-8") as f:
            sample_text = f.read()
    else:
        sample_text = (
            "서울 강남구에서 열린 기술 컨퍼런스에서 김민수 교수가 인공지능의 미래에 대한 강연을 했다. "
            "이번 행사는 삼성전자와 네이버가 공동 주최했으며, 약 500명의 전문가들이 참석했다. "
            "김민수 교수는 서울대학교 컴퓨터공학과 소속으로, 인공지능 발전의 윤리적 측면을 강조했다. "
            "네이버의 이기획 부사장은 회사의 새로운 AI 서비스를 소개했으며, 삼성전자의 정기술 상무가 반도체 기술과 AI의 연관성에 대해 발표했다. "
            "행사 후 김민수 교수와 이기획 부사장은 한국 AI 산업의 발전 방향에 대해 토론했으며, "
            "서울대학교와 네이버의 산학협력 가능성도 언급되었다. "
            "한편, 과학기술정보통신부 안장관은 인공지능 산업 지원 정책을 발표하며, 삼성전자의 연구 프로젝트에 정부 지원을 약속했다."
        )
    
    # 지식 그래프 추출기 생성 및 실행
    extractor = KnowledgeGraphExtractor(api_key=api_key)
    result = extractor.extract(sample_text)
    
    if result["success"]:
        data = result["data"]
        print(f"추출된 개체: {len(data['data']['entities'])}개")
        print(f"추출된 관계: {len(data['data']['relations'])}개")
        print("\n그래프 메트릭:")
        print(f"- 노드 수: {data['metrics']['node_count']}")
        print(f"- 엣지 수: {data['metrics']['edge_count']}")
        print(f"- 그래프 밀도: {data['metrics']['density']:.4f}")
        print(f"\nJSONL 파일: {data['files']['jsonl']}")
        print(f"Entities CSV: {data['files']['entities_csv']}")
        print(f"Relations CSV: {data['files']['relations_csv']}")
        print(f"Relations with Info CSV: {data['files']['relations_with_info_csv']}")
        print(f"정적 그래프 이미지: {data['files']['image']}")
        print(f"인터랙티브 그래프 HTML: {data['files']['html']}")
    else:
        print(f"오류: {result['message']}")

