import base64
import pandas as pd
from io import BytesIO
import streamlit as st
import numpy as np
import re

# 개체 유형별 색상 매핑
COLOR_MAP = {
    "PERSON": "#3498db",      # 파란색
    "ORGANIZATION": "#2ecc71", # 녹색
    "LOCATION": "#e74c3c",    # 빨간색
    "EVENT": "#f39c12",       # 주황색
    "PRODUCT": "#9b59b6",     # 보라색
    "OTHER": "#7f8c8d"        # 회색
}

def get_color_by_entity_type(entity_type):
    """
    개체 유형에 따른 색상을 반환합니다.
    
    매개변수:
        entity_type (str): 개체 유형 (PERSON, ORGANIZATION 등)
        
    반환값:
        str: 해당 유형의 색상 코드
    """
    return COLOR_MAP.get(entity_type, COLOR_MAP["OTHER"])

def get_base64_of_bin_file(bin_file):
    """
    바이너리 파일을 base64로 인코딩하여 반환합니다.
    
    매개변수:
        bin_file (str): 파일 경로
        
    반환값:
        str: base64로 인코딩된 문자열
    """
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def set_background(png_file):
    """
    Streamlit 앱의 배경 이미지를 설정합니다.
    
    매개변수:
        png_file (str): 이미지 파일 경로
    """
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = '''
    <style>
    .stApp {
        background-image: url("data:image/png;base64,%s");
        background-size: cover;
    }
    </style>
    ''' % bin_str
    st.markdown(page_bg_img, unsafe_allow_html=True)

def dataframe_to_excel_bytes(df_dict):
    """
    데이터프레임 사전을 Excel 파일로 변환하여 바이트 형태로 반환합니다.
    
    매개변수:
        df_dict (dict): 시트명을 키로, 데이터프레임을 값으로 갖는 사전
        
    반환값:
        bytes: Excel 파일의 바이트 데이터
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in df_dict.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    output.seek(0)
    return output.read()

def find_entities_in_text(text, entities):
    """
    텍스트에서 개체를 찾아 하이라이팅합니다.
    
    매개변수:
        text (str): 원본 텍스트
        entities (list): 개체 목록
        
    반환값:
        str: 하이라이팅된 HTML 텍스트
    """
    result = text
    # 개체 이름 기준으로 정렬 (긴 이름이 먼저 대체되도록)
    sorted_entities = sorted(entities, key=lambda x: len(x["name"]), reverse=True)
    
    for entity in sorted_entities:
        name = entity["name"]
        entity_type = entity["type"]
        color = get_color_by_entity_type(entity_type)
        
        # 정규표현식 패턴 (단어 경계 고려)
        pattern = r'(\b' + re.escape(name) + r'\b)'
        replacement = f'<span style="background-color: {color}; padding: 2px 4px; border-radius: 3px;">{name}</span>'
        result = re.sub(pattern, replacement, result)
    
    return result

def entity_stats(entities):
    """
    개체 유형별 통계를 계산합니다.
    
    매개변수:
        entities (list): 개체 목록
        
    반환값:
        dict: 유형별 개수
    """
    stats = {}
    for entity in entities:
        entity_type = entity["type"]
        if entity_type in stats:
            stats[entity_type] += 1
        else:
            stats[entity_type] = 1
    return stats

def relation_stats(relations):
    """
    관계 유형별 통계를 계산합니다.
    
    매개변수:
        relations (list): 관계 목록
        
    반환값:
        dict: 유형별 개수
    """
    stats = {}
    for relation in relations:
        relation_type = relation["relation"]
        if relation_type in stats:
            stats[relation_type] += 1
        else:
            stats[relation_type] = 1
    return stats

def get_jsonl_text(entities, relations):
    """
    개체와 관계를 JSONL 형식으로 반환합니다.
    
    매개변수:
        entities (list): 개체 목록
        relations (list): 관계 목록
        
    반환값:
        str: JSONL 형식의 텍스트
    """
    jsonl_lines = []
    
    for entity in entities:
        jsonl_lines.append(json.dumps({"type": "entity", "data": entity}, ensure_ascii=False))
    
    for relation in relations:
        jsonl_lines.append(json.dumps({"type": "relation", "data": relation}, ensure_ascii=False))
    
    return '\n'.join(jsonl_lines)
