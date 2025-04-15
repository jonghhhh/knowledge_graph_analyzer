import os
import json
import re
import pandas as pd
import google.generativeai as genai
from typing import Dict, Any, List

class KnowledgeGraphExtractor:
    """지식 그래프 데이터 추출기 
    - jsonl(json 추가)과 csv(entities, relations, 결합) 5개 파일 생성"""
    
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
        
        # Gemini API 설정
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={"temperature": self.temperature}
            )
        else:
            print("경고: API 키가 설정되지 않았습니다. extract_with_llm 함수는 작동하지 않습니다.")
            self.model = None


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
        
        # API 키 확인
        if not self.api_key:
            # API 키가 없으면 규칙 기반으로 추출
            data = self._extract_with_rules(text)
        else:
            # API 키가 있으면 LLM으로 추출
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
        if not self.api_key:
            raise ValueError("Google API 키가 설정되지 않았습니다")
        
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
    
    def _extract_with_rules(self, text):
        """
        규칙 기반 방식으로 개체와 관계 추출 (API 키가 없을 때 폴백으로 사용)
        
        매개변수:
            text (str): 분석할 텍스트
            
        반환값:
            dict: 추출된 개체와 관계 정보
        """
        # 인물, 조직, 장소 패턴
        patterns = {
            'PERSON': r'([가-힣]{2,4})\s+(?:씨|교수|박사|부장|과장|대표|사장|회장|이사|부사장|상무|이사장|총장|장관|의원|위원|선생님)',
            'ORGANIZATION': r'([가-힣a-zA-Z0-9]+(?:대학교|회사|기업|연구소|협회|재단|센터|그룹|학회|부|과|팀|실|국|처|청|부서))',
            'LOCATION': r'([가-힣]+(?:시|도|군|구|동|읍|면|리|국가|나라))'
        }
        
        entities = []
        entity_map = {}  # 중복 방지를 위한 맵
        entity_id = 1
        
        # 개체 추출
        for entity_type, pattern in patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                entity_name = match.group(1)
                if entity_name not in entity_map:
                    entity_id_str = f"E{entity_id}"
                    entities.append({
                        "id": entity_id_str,
                        "name": entity_name,
                        "type": entity_type,
                        "description": f"{entity_name}은(는) {entity_type} 유형의 개체입니다."
                    })
                    entity_map[entity_name] = entity_id_str
                    entity_id += 1
        
        # 관계 추출 (간단한 근접성 기반)
        relations = []
        relation_id = 1
        
        # 문장 단위로 분리
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # 해당 문장에 있는 개체 찾기
            sentence_entities = []
            for entity_name, entity_id in entity_map.items():
                if entity_name in sentence:
                    entity_info = next((e for e in entities if e["id"] == entity_id), None)
                    if entity_info:
                        sentence_entities.append(entity_info)
            
            # 문장 내 개체 쌍 간의 관계 생성
            for i in range(len(sentence_entities)):
                for j in range(i+1, len(sentence_entities)):
                    source = sentence_entities[i]
                    target = sentence_entities[j]
                    
                    # 관계 유형 결정 (간단한 규칙)
                    relation_type = "관련됨"
                    
                    if source["type"] == "PERSON" and target["type"] == "ORGANIZATION":
                        relation_type = "소속"
                    elif source["type"] == "ORGANIZATION" and target["type"] == "PERSON":
                        relation_type = "고용"
                    elif source["type"] == "PERSON" and target["type"] == "PERSON":
                        relation_type = "협업"
                    elif source["type"] == "ORGANIZATION" and target["type"] == "ORGANIZATION":
                        relation_type = "제휴"
                    elif source["type"] == "LOCATION" or target["type"] == "LOCATION":
                        relation_type = "위치"
                    
                    relations.append({
                        "source": source["id"],
                        "target": target["id"],
                        "relation": relation_type,
                        "sentence": sentence
                    })
                    relation_id += 1
        
        return {
            "entities": entities,
            "relations": relations
        }
