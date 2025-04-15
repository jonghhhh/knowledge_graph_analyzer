# 한국어 지식 그래프 생성기 (Korean Knowledge Graph Generator)

한국어 텍스트에서 개체(Entity)와 관계(Relation)를 추출하여 지식 그래프로 시각화하는 Streamlit 애플리케이션입니다.

![Screenshot](https://github.com/your-username/korean-knowledge-graph-streamlit/raw/main/screenshot.png)

## 📌 주요 기능

- **텍스트 분석**: 한국어 텍스트에서 개체(인물, 조직, 장소 등)와 관계를 자동으로 추출
- **그래프 시각화**: 추출된 개체와 관계를 네트워크 그래프로 시각화
- **데이터 내보내기**: 추출된 데이터를 CSV, JSON, JSONL 형식으로 다운로드
- **API 연동**: Google Gemini API를 사용한 고품질 지식그래프 추출
- **한글 지원**: 모든 과정에서 한글이 깨지지 않도록 설계

## 🔧 설치 방법

### 로컬에서 실행하기

1. 저장소 복제
```bash
git clone https://github.com/your-username/korean-knowledge-graph-streamlit.git
cd korean-knowledge-graph-streamlit
```

2. 가상 환경 생성 및 활성화
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python -m venv venv
source venv/bin/activate
```

3. 필요한 패키지 설치
```bash
pip install -r requirements.txt
```

4. Streamlit 앱 실행
```bash
streamlit run app.py
```

5. 웹 브라우저에서 http://localhost:8501 접속

### Docker로 실행하기

```bash
docker build -t knowledge-graph-app .
docker run -p 8501:8501 knowledge-graph-app
```

## 🚀 사용법

1. **API 키 설정**: 
   - Google AI Studio(https://makersuite.google.com/app/apikey)에서 Gemini API 키 발급
   - 앱의 사이드바에 API 키 입력
   
2. **텍스트 입력**:
   - 분석할 한국어 텍스트 입력
   - 또는 "샘플 텍스트 불러오기" 버튼 클릭하여 예시 사용
   
3. **분석 및 시각화**:
   - "분석하기" 버튼을 클릭하여 지식 그래프 생성
   - 시각화된 그래프에서 노드와 엣지 상호작용 가능
   
4. **데이터 내보내기**:
   - "내보내기" 탭에서 데이터를 CSV, JSON, JSONL 형식으로 다운로드

## 📊 지원하는 개체 유형

- **인물 (PERSON)**: 사람, 인물
- **조직 (ORGANIZATION)**: 회사, 정부, 기관, 단체 등
- **장소 (LOCATION)**: 국가, 도시, 지역 등
- **이벤트 (EVENT)**: 행사, 사건, 회의 등
- **제품 (PRODUCT)**: 제품, 서비스, 기술 등
- **기타 (OTHER)**: 기타 중요 개체

## 🔗 관계 유형 예시

- **소속**: 인물이 조직에 소속됨
- **고용**: 조직이 인물을 고용함
- **협업**: 인물과 인물 사이의 협력 관계
- **제휴**: 조직과 조직 사이의 제휴 관계
- **위치**: 개체와 장소의 관계
- **관련됨**: 기타 관련 관계

## 🌐 배포하기

이 애플리케이션은 [Render](https://render.com)에 무료로 배포할 수 있습니다:

1. Render 계정 생성 및 로그인
2. 새 웹 서비스 추가
3. GitHub 저장소 연결
4. 다음 설정으로 배포:
   - 빌드 명령어: `pip install -r requirements.txt`
   - 시작 명령어: `streamlit run app.py`
   - 환경 변수: `GOOGLE_API_KEY` (선택 사항)

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🔧 기술 스택

- **Streamlit**: 웹 인터페이스
- **Google Generative AI (Gemini)**: 텍스트 분석
- **Streamlit-AgGraph**: 네트워크 그래프 시각화
- **Pandas**: 데이터 처리
- **Python**: 백엔드 로직

## 🙏 기여하기

이슈와 풀 리퀘스트는 환영합니다. 주요 변경 사항의 경우, 먼저 이슈를 열어 논의해주세요.
