import asyncio
from telegram import Bot
import logging
from datetime import datetime
import json
import os
import urllib.request
import urllib.parse

# 로깅 설정
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 텔레그램 설정
NAVER_CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]


# 키워드 목록
SEARCH_KEYWORDS = [
    "풍력", "터빈", "풍력 발전기", "풍력 타워", "Vestas", 
    "베스타스", "SGRE", "지멘스 가메사", "Enercon", "에너콘", 
    "GE 풍력", "Mingyang","밍양", "유니슨", "코오롱글로벌 풍력", "풍력 EPC"
]

# 뉴스 개수
MAX_ARTICLES = 5

# 데이터 저장 파일
DATA_FILE = "last_sent_news.json"

# NAVER API 인증 정보
NAVER_CLIENT_ID = "Q26WbLexV6MzchaO6MsZ"
NAVER_CLIENT_SECRET = "y9X5XPMpNX"

# 전송 기록 불러오기
def load_sent_news():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# 전송 기록 저장
def save_sent_news(sent_data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(sent_data, f, ensure_ascii=False, indent=2)

# 뉴스 불러오기
def get_news_from_naver_api(keyword):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display=10&sort=date"

    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", NAVER_CLIENT_ID)
    request.add_header("X-Naver-Client-Secret", NAVER_CLIENT_SECRET)

    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            result = json.loads(response.read().decode('utf-8'))
            return result['items']
    except Exception as e:
        logger.error(f"API 호출 실패: {e}")
    return []

# 새로운 뉴스 필터링
def filter_new_news(keyword, news_list, sent_data):
    sent_links = sent_data.get(keyword, [])
    new_news = []
    new_links = []

    for news in news_list:
        if news['link'] not in sent_links:
            new_news.append(news)
            new_links.append(news['link'])
        if len(new_news) >= MAX_ARTICLES:
            break

    if new_links:
        sent_data[keyword] = new_links + sent_links
        if len(sent_data[keyword]) > 100:
            sent_data[keyword] = sent_data[keyword][:100]
    
    return new_news

# 텔레그램 전송
async def send_to_telegram(keyword, articles):
    if not articles:
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    message = f"<b>{keyword}</b> 관련 뉴스 ({now})\n\n"
    for i, article in enumerate(articles, 1):
        title = article['title'].replace("<b>", "").replace("</b>", "").replace("\"", "\"").replace("<", "<").replace(">", ">").replace("&", "&")
        link = article['link']
        message += f"{i}. {title}\n{link}\n\n"

    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode='HTML',
            disable_web_page_preview=True  # 웹 페이지 미리보기 비활성화
        )
        logger.info(f"[{keyword}] 전송 완료 ({len(articles)}건)")
    except Exception as e:
        logger.error(f"[{keyword}] 전송 실패: {e}")

# 메인 작업
async def main_task():
    logger.info("뉴스 수집 시작")
    sent_data = load_sent_news()

    for keyword in SEARCH_KEYWORDS:
        logger.info(f"[{keyword}] 뉴스 수집 중...")
        news_list = get_news_from_naver_api(keyword)
        logger.info(f"[{keyword}] 총 {len(news_list)}개 수집됨")

        new_news = filter_new_news(keyword, news_list, sent_data)
        logger.info(f"[{keyword}] 새 뉴스 {len(new_news)}개 발견")

        await send_to_telegram(keyword, new_news)

    save_sent_news(sent_data)
    logger.info("작업 완료")

# 메인 실행
def main():
    asyncio.run(main_task())

if __name__ == "__main__":
    main()
