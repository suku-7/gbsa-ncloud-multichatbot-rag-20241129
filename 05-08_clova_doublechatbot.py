import requests
import json
import streamlit as st
from serpapi import GoogleSearch
import os  # .env 파일 관리를 위해 os 라이브러리 추가
from dotenv import load_dotenv  # .env 파일 로드를 위한 라이브러리 추가

# .env 파일에서 환경 변수 불러오기
load_dotenv()

# Naver Clova API 정보
CLOVA_HOST = os.getenv("CLOVA_HOST")
CLOVA_API_KEY = os.getenv("CLOVA_API_KEY")
CLOVA_API_KEY_PRIMARY_VAL = os.getenv("CLOVA_API_KEY_PRIMARY_VAL")
CLOVA_REQUEST_ID = os.getenv("CLOVA_REQUEST_ID")

# SerpAPI 정보
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

class CompletionExecutor:
    def __init__(self, host, api_key, api_key_primary_val, request_id):
        self._host = host
        self._api_key = api_key
        self._api_key_primary_val = api_key_primary_val
        self._request_id = request_id

    def execute(self, completion_request):
        headers = {
            'X-NCP-CLOVASTUDIO-API-KEY': self._api_key,
            'X-NCP-APIGW-API-KEY': self._api_key_primary_val,
            'X-NCP-CLOVASTUDIO-REQUEST-ID': self._request_id,
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': 'text/event-stream'
        }

        response = requests.post(
            self._host + '/testapp/v1/chat-completions/HCX-DASH-001',
            headers=headers,
            json=completion_request,
            stream=True
        )
        
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    # `data:` 부분 제거 후 JSON 파싱
                    data_str = line.decode("utf-8")
                    if data_str.startswith('data:'):
                        data_str = data_str[5:]
                    
                    data = json.loads(data_str)
                    if "message" in data and data["message"]["role"] == "assistant":
                        content = data["message"]["content"]
                        full_response += content
                except json.JSONDecodeError:
                    # 가끔 발생하는 빈 줄이나 다른 이벤트 데이터를 무시
                    continue
                except Exception as e:
                    print(f"An error occurred: {e}") # 디버깅을 위한 에러 출력
                    continue
        
        return full_response.strip()

# 대화 상태 저장
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Streamlit UI 설정
st.title('🍚점심시간에 뭐먹지?🤔 Chatbot')
st.markdown("예시: `성수동 성수낙낙 근처 한식 맛집 알려줘`")

# 텍스트 입력
user_input = st.text_input("질문을 입력하세요:")

if user_input:
    # 사용자 입력 저장
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 프롬프트 구성
    system_prompt = "- 해당 지역을 자세히 알고있는 주민이고 근처 식당들을 다양하게 다녀본 직장인입니다.\n" \
                    "- 존댓말을 사용해서 친절하게 설명합니다.\n" \
                    "- 초등학생도 이해할 수 있도록 직관적인 비유를 사용하여 설명합니다.\n" \
                    "- 답변할 때마다 \"CLOVA 검색결과 : \" 문장을 추가합니다." \
                    "- 정확한 정보를 바탕으로 설명하며 다양한 관점을 반영합니다.\n"

    preset_text = [{"role": "system", "content": system_prompt}] + st.session_state.messages

    request_data = {
        'messages': preset_text,
        'topP': 0.6,
        'topK': 0,
        'maxTokens': 512,
        'temperature': 0.5,
        'repeatPenalty': 5.0,
        'stopBefore': [],
        'includeAiFilters': True,
        'seed': 0
    }

    with st.spinner("CLOVA가 답변을 생성중입니다..."):
        # Clova API 실행
        completion_executor = CompletionExecutor(
            host=CLOVA_HOST,
            api_key=CLOVA_API_KEY,
            api_key_primary_val=CLOVA_API_KEY_PRIMARY_VAL,
            request_id=CLOVA_REQUEST_ID
        )
        response = completion_executor.execute(request_data)

    # 챗봇의 답변 저장
    st.session_state.messages.append({"role": "assistant", "content": response})

    with st.spinner("SerpAPI로 관련 정보를 검색중입니다..."):
        # SerpAPI 검색 파라미터 설정
        search_params = {
            "q": response,  # 검색어를 Clova 답변으로 설정
            "location": "Seoul, South Korea",
            "hl": "ko",
            "gl": "kr",
            "google_domain": "google.com",
            "api_key": SERPAPI_API_KEY
        }

        search = GoogleSearch(search_params)
        search_results = search.get_dict()

    # SerpAPI 결과를 포맷팅하여 저장
    search_output_lines = ["\n\n--- SerpAPI 검색 결과 ---"]
    organic_results = search_results.get("organic_results", [])
    if organic_results:
        for result in organic_results[:3]: # 상위 3개 결과만 표시
             search_output_lines.append(f"- **{result.get('title', '제목 없음')}**: [링크]({result.get('link', '#')})")
    else:
        search_output_lines.append("관련 검색 결과를 찾을 수 없습니다.")
    
    search_output = "\n".join(search_output_lines)

    # 대화 내용에 SerpAPI 결과 추가
    st.session_state.messages.append({"role": "assistant", "content": search_output})

# 전체 대화 내용 다시 출력
# st.experimental_rerun()을 사용하면 입력 후 바로 전체 대화가 갱신됩니다.
# 하지만 이 경우 루프가 발생할 수 있으므로, 마지막에 한 번만 전체를 그리는 방식으로 유지합니다.

# 대화 내용 출력
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

