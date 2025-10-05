import gspread
from google.oauth2.service_account import Credentials
from colorama import Fore, Style, init
from datetime import datetime
import requests
import time
import threading
import os
import subprocess
from gtts import gTTS
import uuid
import settings
from pystyle import Colors, Write

init(autoreset=True)

def dp(msg):
    if settings.디버그_모드:
        print(Fore.GREEN + msg + Style.RESET_ALL)

CHAT_WEBHOOK_URLS = settings.지챗_웹훅_링크
CURRENT_WEBHOOK_USING_IDX=0
LOG_QUEUE=[]
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)
dp('creds 로딩 성공')
client = gspread.authorize(creds)
dp('creds authorize 성공')
t=time.time()
spreadsheet = client.open_by_key(settings.스프레드시트_키)
sheet = spreadsheet.sheet1
if settings.로딩중_전체표시:
    print(Fore.BLUE+"스프레드시트 로딩완료")
if settings.로딩소요시간_표시 and settings.로딩중_전체표시:
    print(Fore.YELLOW+f"스프레드시트 로딩 소요 시간: {round(time.time()-t,3)}초")

try:
    t=time.time()
    log_sheet = spreadsheet.worksheet(settings.로깅시트_이름)
    dp('log_sheet 로딩 성공')
except gspread.WorksheetNotFound:
    log_sheet = spreadsheet.add_worksheet(title=settings.로깅시트_이름, rows=settings.로깅시트_세로열, cols=settings.로깅시트_가로열)
    log_sheet.append_row(["이름", "ID카드 정보", "상태", "시간", "노트"])
    dp('log_sheet 감지안됌, 생성 성공')
if settings.로딩중_전체표시:
    print(Fore.BLUE+"로그시트 로딩완료")
if settings.로딩소요시간_표시 and settings.로딩중_전체표시:
    print(Fore.YELLOW+f"로그시트 로딩 소요 시간: {round(time.time()-t,3)}초")

if settings.로딩중_기숙사표시:
    Write.Print(f"{settings.기숙사_이름} 기숙사용 프로그램 로딩중...\n", Colors.red_to_purple, interval=0.03)
    time.sleep(settings.로딩중_기숙사_지연시간)

print('\033c',end='')


def txtc(msg,name,id):
    msg=msg.replace('%time',datetime.now().strftime("%H:%M:%S"))
    msg=msg.replace('%date',datetime.now().strftime("%Y-%m-%d"))
    msg=msg.replace('%name',str(name))
    msg=msg.replace('%id',id)
    return msg

def speak(text: str, speed=settings.음성출력_배속):
    if settings.음성출력:
        tts = gTTS(text=text, lang='ko')
        uid=uuid.uuid4()
        tts.save(f"tts_{uid}.mp3")
        dp(f'tts_{uid}.mp3 저장 성공')
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-af", f"atempo={speed}", f"tts_{uid}.mp3"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        try:
            os.remove(f"tts_{uid}.mp3")
            dp(f'tts_{uid}.mp3 삭제 성공')
        except Exception as e:
            print(Fore.RED + f"tts_{uid}.mp3 삭제 실패: {e}" + Style.RESET_ALL)


def send_to_gchat(message: str, retry=0):
    if settings.지챗전송:
        global CURRENT_WEBHOOK_USING_IDX

        """Google Chat으로 메시지 전송"""
        payload = {"text": message}
        CHAT_WEBHOOK_URL=CHAT_WEBHOOK_URLS[CURRENT_WEBHOOK_USING_IDX]
        # CURRENT_WEBHOOK_USING_IDX=1-CURRENT_WEBHOOK_USING_IDX # 2개일시만 작동함(구코드)
        CURRENT_WEBHOOK_USING_IDX= 0 if CURRENT_WEBHOOK_USING_IDX==len(CHAT_WEBHOOK_URLS)-1 else CURRENT_WEBHOOK_USING_IDX+1

        try:
            response = requests.post(CHAT_WEBHOOK_URL, json=payload)
            dp(f'지챗 전송 성공, using webhook no#{CURRENT_WEBHOOK_USING_IDX}')
            if response.status_code != 200:
                if retry==0:
                    print(Fore.RED + f"지챗 전송 실패: {response.text}" + Style.RESET_ALL)
                else:
                    print(Fore.RED + f"[{retry+1}/{settings.지챗_재전송시도횟수}]지챗 재전송 실패: {response.text}" + Style.RESET_ALL)
                if settings.지챗_재전송시도 and retry!=settings.지챗_재전송시도횟수:
                    time.sleep(settings.지챗_재전송멈춤시간)
                    print(Fore.YELLOW + "재전송 시도중..")
                    send_to_gchat(f'[{retry+1}/{settings.지챗_재전송시도횟수}번째 재전송 시도된 메세지]\n'+message, retry+1)
                if retry==settings.지챗_재전송시도횟수:
                    print(Fore.RED + f"지챗 전체 횟수 시도 재전송 실패: {response.text}" + Style.RESET_ALL)

        except Exception as e:
            print(Fore.RED + f"지챗 에러: {e}" + Style.RESET_ALL)

def make_logs():
    while True:
        time.sleep(0.1)
        if LOG_QUEUE:
            log_sheet.append_row(
                LOG_QUEUE[0],
                table_range="A1"   # 항상 A열부터 시작
            )
            LOG_QUEUE.remove(LOG_QUEUE[0])


def check_id(card_id: str):
    """ID카드를 확인하고 상태를 토글 + 로그 시트에 기록 + 지챗 알림"""
    data = sheet.get_all_values()
    found = False

    for row_idx, row in enumerate(data[1:], start=2):
        if len(row) >= 2 and row[1] == card_id:
            found = True
            name = row[0]
            status = row[2] if len(row) > 2 else "외출"
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if status == "출입":
                new_status = "외출"
                msg=txtc(settings.지챗_외출메세지,name,card_id)
                print(Fore.RED + txtc(settings.터미널출력_메세지_외출,name,card_id) + Style.RESET_ALL + "\n")
                threading.Thread(target=speak, args=(txtc(settings.음성출력_메세지_외출,name,card_id),),daemon=True).start()

            else:
                new_status = "출입"
                msg=txtc(settings.지챗_출입메세지,name,card_id)
                print(Fore.GREEN + txtc(settings.터미널출력_메세지_출입,name,card_id) + Style.RESET_ALL + "\n")
                threading.Thread(target=speak, args=(txtc(settings.음성출력_메세지_출입,name,card_id),),daemon=True).start()
            
            # Google Chat 알림 보내기
            threading.Thread(target=send_to_gchat, args=(msg,)).start()

            # 시트 업데이트
            sheet.update_cell(row_idx, 3, new_status)
            sheet.update_cell(row_idx, 4, f"{now} - {new_status}")
            LOG_QUEUE.append([name, card_id, new_status, now])
            dp(f'시트 업데이트 성공, row#{row_idx}, status#{new_status}')
            break

    if not found:
        print(Fore.YELLOW + settings.터미널출력_없는정보 + Style.RESET_ALL)
        threading.Thread(target=speak, args=(txtc(settings.음성출력_없는정보,None,card_id),),daemon=True).start()
        if settings.지챗_없는정보메세지:
            send_to_gchat(txtc(settings.지챗_없는정보메세지,None,card_id))


if __name__ == "__main__":
    if settings.로깅시트사용:
        threading.Thread(target=make_logs, args=(),daemon=True).start()
        dp('make_logs 스레드 생성 성공')
    while True:
        Write.Print(f"[{settings.기숙사_이름} 기숙사용]\n", Colors.red_to_purple,interval=0)
        card_id = input(Fore.CYAN + "ID카드를 입력하세요 (종료는 q): " + Style.RESET_ALL)
        if not card_id:
            continue
        if card_id.lower() == "q":
            print(Fore.MAGENTA + "프로그램을 종료합니다." + Style.RESET_ALL)
            break
        check_id(card_id)
        if settings.카드체크후_메세지지우기:
            print('\033c',end='')
