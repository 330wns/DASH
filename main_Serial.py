#DASH with NFC
"""지원이 종료되었습니다. 출입시간 경고 기능부터 사용이 지원되지 않습니다."""

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
from smartcard.System import readers
from smartcard.util import toHexString

init(autoreset=True)

# =====================================================
# 기본 초기화
# =====================================================
def dp(msg):
    if settings.디버그_모드:
        print(Fore.GREEN + msg + Style.RESET_ALL)

CHAT_WEBHOOK_URLS = settings.지챗_웹훅_링크
CURRENT_WEBHOOK_USING_IDX = 0
LOG_QUEUE = []

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

t = time.time()
spreadsheet = client.open_by_key(settings.스프레드시트_키)
sheet = spreadsheet.sheet1
if settings.로딩중_전체표시:
    print(Fore.BLUE + "스프레드시트 로딩완료")
if settings.로딩소요시간_표시 and settings.로딩중_전체표시:
    print(Fore.YELLOW + f"스프레드시트 로딩 소요 시간: {round(time.time()-t, 3)}초")

try:
    t = time.time()
    log_sheet = spreadsheet.worksheet(settings.로깅시트_이름)
    dp('log_sheet 로딩 성공')
except gspread.WorksheetNotFound:
    log_sheet = spreadsheet.add_worksheet(
        title=settings.로깅시트_이름,
        rows=settings.로깅시트_세로열,
        cols=settings.로깅시트_가로열
    )
    log_sheet.append_row(["이름", "ID카드 정보", "상태", "시간", "노트"])
    dp('log_sheet 감지안됌, 생성 성공')

if settings.로딩중_전체표시:
    print(Fore.BLUE + "로그시트 로딩완료")
if settings.로딩소요시간_표시 and settings.로딩중_전체표시:
    print(Fore.YELLOW + f"로그시트 로딩 소요 시간: {round(time.time()-t, 3)}초")

if settings.로딩중_기숙사표시:
    Write.Print(f"{settings.기숙사_이름} 기숙사용 프로그램 로딩중...\n", Colors.red_to_purple, interval=0.03)
    time.sleep(settings.로딩중_기숙사_지연시간)

print('\033c', end='')

# =====================================================
# 공통 함수
# =====================================================
def txtc(msg, name, id):
    msg = msg.replace('%time', datetime.now().strftime("%H:%M:%S"))
    msg = msg.replace('%date', datetime.now().strftime("%Y-%m-%d"))
    msg = msg.replace('%name', str(name))
    msg = msg.replace('%id', id)
    return msg


def speak(text: str, speed=settings.음성출력_배속):
    if settings.음성출력:
        tts = gTTS(text=text, lang=settings.음성출력_언어)
        uid = uuid.uuid4()
        filename = f"tts_{uid}.mp3"
        tts.save(filename)
        dp(f'{filename} 저장 성공')
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", "-af", f"atempo={speed}", filename],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        try:
            os.remove(filename)
            dp(f'{filename} 삭제 성공')
        except Exception as e:
            print(Fore.RED + f"{filename} 삭제 실패: {e}" + Style.RESET_ALL)


def send_to_gchat(message: str):
    if settings.지챗전송:
        global CURRENT_WEBHOOK_USING_IDX
        payload = {"text": message}
        CHAT_WEBHOOK_URL = CHAT_WEBHOOK_URLS[CURRENT_WEBHOOK_USING_IDX]
        CURRENT_WEBHOOK_USING_IDX = 0 if CURRENT_WEBHOOK_USING_IDX == len(CHAT_WEBHOOK_URLS) - 1 else CURRENT_WEBHOOK_USING_IDX + 1

        try:
            response = requests.post(CHAT_WEBHOOK_URL, json=payload)
            dp(f'지챗 전송 성공, using webhook no#{CURRENT_WEBHOOK_USING_IDX}')
            if response.status_code != 200:
                print(Fore.RED + f"지챗 전송 실패: {response.text}" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"지챗 에러: {e}" + Style.RESET_ALL)


def make_logs():
    while True:
        time.sleep(0.1)
        if LOG_QUEUE:
            log_sheet.append_row(LOG_QUEUE[0], table_range="A1")
            LOG_QUEUE.remove(LOG_QUEUE[0])


def check_id(card_id: str):
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
                msg = txtc(settings.지챗_외출메세지, name, card_id)
                print(Fore.RED + txtc(settings.터미널출력_메세지_외출, name, card_id) + Style.RESET_ALL + "\n")
                threading.Thread(target=speak, args=(txtc(settings.음성출력_메세지_외출, name, card_id),), daemon=True).start()
            else:
                new_status = "출입"
                msg = txtc(settings.지챗_출입메세지, name, card_id)
                print(Fore.GREEN + txtc(settings.터미널출력_메세지_출입, name, card_id) + Style.RESET_ALL + "\n")
                threading.Thread(target=speak, args=(txtc(settings.음성출력_메세지_출입, name, card_id),), daemon=True).start()

            threading.Thread(target=send_to_gchat, args=(msg,), daemon=True).start()
            sheet.update_cell(row_idx, 3, new_status)
            sheet.update_cell(row_idx, 4, f"{now} - {new_status}")
            LOG_QUEUE.append([name, card_id, new_status, now])
            dp(f'시트 업데이트 성공, row#{row_idx}, status#{new_status}')
            break

    if not found:
        print(Fore.YELLOW + settings.터미널출력_없는정보 + Style.RESET_ALL)
        threading.Thread(target=speak, args=(txtc(settings.음성출력_없는정보, None, card_id),), daemon=True).start()
        if settings.지챗_없는정보메세지:
            send_to_gchat(txtc(settings.지챗_없는정보메세지, None, card_id))


# =====================================================
# 카드 리더 자동 감지 루프
# =====================================================
def auto_read_cards():
    reader_list = readers()
    if not reader_list:
        print("리더를 찾을 수 없습니다. 연결 및 드라이버 확인 필요.")
        return

    reader = reader_list[0]
    print(Fore.MAGENTA + f"사용 리더: {reader}" + Style.RESET_ALL)
    print(Fore.CYAN + "ID카드를 태깅해주세요 (종료: Ctrl+C)" + Style.RESET_ALL)

    while True:
        try:
            connection = reader.createConnection()
            # 카드 올릴 때까지 대기
            while True:
                try:
                    connection.connect()
                    break
                except Exception:
                    time.sleep(0.3)
                    continue

            # UID 읽기
            GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.transmit(GET_UID_APDU)

            if sw1 == 0x90 and sw2 == 0x00:
                uid = toHexString(data).replace(" ", "")
                print(Fore.CYAN + f"감지된 UID: {uid}" + Style.RESET_ALL)
                check_id(uid)
            else:
                print(Fore.YELLOW + "UID 읽기 실패 또는 카드 미인식" + Style.RESET_ALL)
                speak('카드를 다시 대주세요',1.7)

            # 카드 뗄 때까지 대기
            while True:
                try:
                    connection.transmit(GET_UID_APDU)
                    time.sleep(0.4)
                except Exception:
                    break

            connection.disconnect()
            print(Fore.CYAN + "ID카드를 태깅해주세요 (종료: Ctrl+C)" + Style.RESET_ALL)

            time.sleep(0.3)

        except KeyboardInterrupt:
            print("프로그램 종료됨.")
            break
        except Exception:
            time.sleep(0.5)
            continue


# =====================================================
# 메인
# =====================================================
if __name__ == "__main__":
    if settings.로깅시트사용:
        threading.Thread(target=make_logs, daemon=True).start()
        dp('make_logs 스레드 생성 성공')

    Write.Print(f"[{settings.기숙사_이름} 기숙사용]\n", Colors.red_to_purple, interval=0)
    auto_read_cards()
