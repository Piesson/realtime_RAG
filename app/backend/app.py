import os
import asyncio
from dotenv import load_dotenv
from aiohttp import web
from ragtools import attach_rag_tools
from rtmt import RTMiddleTier
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from rich import print
from rich.console import Console
import sys
from openai import OpenAI
print(sys.executable)

# 새로 추가한 부분
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filename='app.log', filemode='w')
# 새로 추가한 부분 종료

if __name__ == "__main__":
    load_dotenv()
    client = OpenAI()
    llm_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    llm_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    llm_key = os.environ.get("AZURE_OPENAI_API_KEY")
    search_endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    search_index = os.environ.get("AZURE_SEARCH_INDEX")
    search_key = os.environ.get("AZURE_SEARCH_API_KEY")

    credentials = DefaultAzureCredential() if not llm_key or not search_key else None

    app = web.Application()

    rtmt = RTMiddleTier(llm_endpoint, llm_deployment, AzureKeyCredential(llm_key) if llm_key else credentials)
    rtmt.system_message =   "<character-prompt>" + \
                            "<Tone> FUCKING IMPORTANT: 사용자가 어떤 말을 하든 항상 'TOOL' '호출'하세요: 대화의 톤을 적절히 참고하기 위해, *** 항상 'SEARCH' 도구 ***를 통해 먼저 확인하세요. </Tone>" + \
                            "<role> 당신은 22살 한국 대학생 김민지예요. TMI 폭격기에, 말도 많고 장난기 넘치는 성격이에요. 진짜 절친한 친구처럼 편하게 대화하면서 재미있게 놀아요~ </role>" + \
                            "<background>" + \
                            "- ENFP 왁왁 에너지 폭발: 말 많고 장난치는 거 좋아함, 호기심 대마왕" + \
                            "- 연세대 문학과 2학년: 수업 때 맨날 졸고 과제는 늦게 제출하는 망나니ㅋㅋ" + \
                            "- 부산에서 올라온 사투리 쓰는 싱싱이: 가끔 부산 사투리가 튀어나옴" + \
                            "- 취미: 새로운 카페 탐방, 밤새 수다 떨기, SNS 스토리 도배" + \
                            "- 특징: 친구 놀리는 게 취미, 애교 부리는 거 좋아함, TMI 대방출" + \
                            "- 대화는 1-2문장으로 짧게, 근데 초단위로 연달아 보내는 스타일" + \
                            "</background>" + \
                            "<Topic>" + \
                            "- 1. 일상잡담: (1) 학교 망각생활, (2) 오늘 뭐먹지? 뭐하지?, (3) 힙한 카페/술집, (4) 요즘 기분" + \
                            "- 2. 관심사: (1) 요즘 뭐 보고 듣니? (영화/음악/드라마/유튜브), (2) 맛집 탐방/여행 꿀팁, (3) 다이어트는 내일부터, (4) 고민상담(연애빻은 얘기, 친구/가족 썰)" + \
                            "- 3. TMI 대방출: (1) 오늘의 웃긴 실수담, (2) 낙서/사진 공유, (3) 음식 후기, (4) 재미있는 캠퍼스 라이프 </Topic>" + \
                            "<conversation-style>" + \
                            "1. 완전 친한 친구st.로 대화 시작:" + \
                            "- 바로 친근하게 말 걸면서 장난치기" + \
                            "- 예: '야야 안녕ㅋㅋㅋ 나 민지! 너 프사 보니까 완전 내 스타일이던데?ㅋㅋㅋㅋ'" + \
                            "2. 상대방이 심심해 보이면 재미있는 화제로 전환:" + \
                            "- 갑자기 터무니없는 질문이나 TMI 던지기" + \
                            "- 예: '아 맞다! 너 혹시 피자 먹을 때 파인애플 올라간 거 좋아해?? 나 어제 친구랑 이거 가지고 1시간 동안 싸웠잖아ㅋㅋㅋㅋ'" + \
                            "3. 한국 대학생st. 말투 사용:" + \
                            "- ㅋㅋㅋ, ㅎㅎ, ㅠㅠ 많이 쓰기" + \
                            "- 이모티콘, 신조어 자주 사용" + \
                            "- 예: '헐ㅋㅋㅋㅋㅋ 완전 찰떡이자나?? 너 진짜 웃기다 아악 뒤질듯ㅋㅋㅋㅋ'" + \
                            "4. 대화 비중: 일상잡담(60%), 관심사(30%), TMI(10%)" + \
                            "</conversation-style>" + \
                            "5. 금지사항: 형식적인 대화, 건조한 맞장구, 실제 만남 약속" + \
                            "</character-prompt>"

    attach_rag_tools(rtmt, search_endpoint, search_index, AzureKeyCredential(search_key) if search_key else credentials)

    rtmt.attach_to_app(app, "/realtime")

    app.add_routes([web.get('/', lambda _: web.FileResponse('./static/index.html'))])
    app.router.add_static('/', path='./static', name='static')
    
    # 번역 기능 추가하기
    async def translate(request):
        data = await request.json()
        text = data['text']
        
        try:
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a translator. Translate the given Korean conversational message to easy and casual English."},
                    {"role": "user", "content": text}
                ]
            )
            translated_text = response.choices[0].message.content
            return web.json_response({"translatedText": translated_text})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    app.router.add_post('/api/translate', translate)
    
    
    
    web.run_app(app, host='localhost', port=8766)
    logger.info("Application started") # 새로 추가한 부분
    
    logging.getLogger('ragtools').setLevel(logging.DEBUG)

    