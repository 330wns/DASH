# DASH Combined Version, Tkinter GUI Version, Alpha

from ast import excepthandler
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import requests
import time
import threading
import os
import subprocess
from gtts import gTTS
import uuid
import settings
from colorama import Fore, Style, init
import importlib
print(Fore.BLUE+'settings.py 로딩 성공')
# NFC 리더기 관련 import (리더기 사용 시에만)
if settings.리더기_사용:
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        NFC_AVAILABLE = True
    except ImportError:
        print("NFC 리더기 라이브러리가 설치되지 않았습니다. 수동 입력 모드로 전환합니다.")
        NFC_AVAILABLE = False
else:
    NFC_AVAILABLE = False

init(autoreset=True)

# =====================================================
# 기본 초기화
# =====================================================
def dp(msg):
    if settings.디버그_모드:
        print(f"[DEBUG] {msg}")

CHAT_WEBHOOK_URLS = settings.지챗_웹훅_링크
CURRENT_WEBHOOK_USING_IDX = 0
LOG_QUEUE = []

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Google Sheets 초기화
try:
    creds = Credentials.from_service_account_file(
        settings.JSON파일_경로,
        scopes=SCOPES
    )
    dp('creds 로딩 성공')
    client = gspread.authorize(creds)
    dp('creds authorize 성공')
    
    spreadsheet = client.open_by_key(settings.스프레드시트_키)
    sheet = spreadsheet.sheet1
    
    # 로그 시트 초기화
    try:
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
        
except Exception as e:
    print(f"Google Sheets 초기화 실패: {e}")
    sheet = None
    log_sheet = None

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
        try:
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
                print(f"{filename} 삭제 실패: {e}")
        except Exception as e:
            print(f"TTS 오류: {e}")

def send_to_gchat(message: str, retry=0):
    if settings.지챗전송:
        global CURRENT_WEBHOOK_USING_IDX
        payload = {"text": message}
        CHAT_WEBHOOK_URL = CHAT_WEBHOOK_URLS[CURRENT_WEBHOOK_USING_IDX]
        CURRENT_WEBHOOK_USING_IDX = 0 if CURRENT_WEBHOOK_USING_IDX == len(CHAT_WEBHOOK_URLS) - 1 else CURRENT_WEBHOOK_USING_IDX + 1
        fail=False
        try:
            response = requests.post(CHAT_WEBHOOK_URL, json=payload)
            if response.status_code != 200:
                fail=True
            elif retry != 0:
                print(Fore.GREEN+'재전송 성공!!')
            dp(f'지챗 {'전송' if retry==0 else '재전송'} 성공, using webhook no#{CURRENT_WEBHOOK_USING_IDX}') if response.status_code == 200 else dp(f'지챗 {'전송' if retry==0 else '재전송'} 실패, using webhook no#{CURRENT_WEBHOOK_USING_IDX}')
        except Exception as e:
            print(f"지챗 에러: {e}")
            fail=True
        if fail:
            if retry == 0:
                try:
                    print(f"지챗 전송 실패: {response.text}")
                except:
                    None
            else:
                print(Fore.RED+f'[{retry+1}/{settings.지챗_재전송시도횟수}]')
                try:
                    print(f"지챗 재전송 실패: {response.text}")
                except:
                    None
            if settings.지챗_재전송시도 and retry != settings.지챗_재전송시도횟수:
                time.sleep(settings.지챗_재전송멈춤시간)
                print("재전송 시도중..")
                send_to_gchat(f'[{retry+1}/{settings.지챗_재전송시도횟수}번째 재전송 시도된 메세지]\n'+message if retry==0 else f'[{retry+1}/{settings.지챗_재전송시도횟수}번째 재전송 시도된 메세지]\n'+'\n'.join(message.split('\n')[1:]), retry+1)
            if retry == settings.지챗_재전송시도횟수:
                print(f"지챗 전체 횟수 시도 재전송 실패")
                try:
                    print(response.text)
                except:
                    None

def make_logs():
    while True:
        time.sleep(0.1)
        if LOG_QUEUE and log_sheet:
            try:
                log_sheet.append_row(LOG_QUEUE[0], table_range="A1")
                LOG_QUEUE.remove(LOG_QUEUE[0])
            except Exception as e:
                print(f"로그 기록 실패: {e}")

def check_id(card_id: str, gui_app):
    if not sheet:
        gui_app.log_message("❌ 스프레드시트 연결 실패", "error")
        return
        
    try:
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
                    # 먼저 메시지 표시
                    gui_app.log_message(f"👋 {txtc(settings.터미널출력_메세지_외출, name, card_id)}", "exit")
                    gui_app.update_status_display(name, "외출")
                    
                else:
                    new_status = "출입"
                    msg = txtc(settings.지챗_출입메세지, name, card_id)
                    # 먼저 메시지 표시
                    gui_app.log_message(f"✅ {txtc(settings.터미널출력_메세지_출입, name, card_id)}", "enter")
                    gui_app.update_status_display(name, "출입")

                # 메시지 표시 후 잠시 대기 (사용자가 메시지를 볼 수 있도록)
                time.sleep(0.5)
                
                # 음성 출력 작업 (추적하지 않음)
                def speak_task():
                    speak(txtc(settings.음성출력_메세지_외출 if status == "출입" else settings.음성출력_메세지_출입, name, card_id))
                threading.Thread(target=speak_task, daemon=True).start()

                # 지챗 전송 작업 (추적하지 않음)
                def gchat_task():
                    send_to_gchat(msg)
                threading.Thread(target=gchat_task, daemon=True).start()
                
                # 스프레드시트와 로그시트 작업만 추적
                gui_app.task_started()  # 스프레드시트 작업 시작
                gui_app.task_started()  # 로그시트 작업 시작
                
                # 스프레드시트 업데이트 작업
                def sheet_task():
                    sheet.update_cell(row_idx, 3, new_status)
                    sheet.update_cell(row_idx, 4, f"{now} - {new_status}")
                    dp(f'시트 업데이트 성공, row#{row_idx}, status#{new_status}')
                    gui_app.task_completed()  # 스프레드시트 작업 완료
                threading.Thread(target=sheet_task, daemon=True).start()
                
                # 로그시트 작업
                def log_task():
                    LOG_QUEUE.append([name, card_id, new_status, now])
                    gui_app.task_completed()  # 로그시트 작업 완료
                threading.Thread(target=log_task, daemon=True).start()
                
                break

        if not found:
            # 먼저 메시지 표시
            gui_app.log_message(f"⚠️ {settings.터미널출력_없는정보}", "warning")
            
            # 메시지 표시 후 잠시 대기
            time.sleep(0.5)
            
            # 음성 출력 작업 (추적하지 않음)
            def speak_task():
                speak(txtc(settings.음성출력_없는정보, None, card_id))
            threading.Thread(target=speak_task, daemon=True).start()
            
            # 지챗 전송 작업 (추적하지 않음)
            if settings.지챗_없는정보메세지:
                def gchat_task():
                    send_to_gchat(txtc(settings.지챗_없는정보메세지, None, card_id))
                threading.Thread(target=gchat_task, daemon=True).start()
            
            # 없는 정보인 경우는 즉시 다음 카드 준비
            if settings.리더기_사용:
                gui_app.current_status_label.config(
                    text="ID카드를 태깅해주세요", foreground="black")
            else:
                gui_app.current_status_label.config(
                    text="ID카드를 입력하세요", foreground="black")
                
    except Exception as e:
        gui_app.log_message(f"❌ 오류 발생: {e}", "error")

# =====================================================
# Tkinter GUI 클래스
# =====================================================
class DormitoryApp:
    def __init__(self, root):
        self.root = root
        mode_text = "NFC" if settings.리더기_사용 else "수동 입력"
        self.root.title(f"{settings.기숙사_이름} 기숙사 출입 관리 시스템 ({mode_text})")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # 카드 리더 상태 (리더기 사용 시에만)
        self.reader_active = False
        self.reader_thread = None
        
        # 작업 완료 추적
        self.pending_tasks = 0
        self.current_processing = False
        
        self.setup_ui()
        self.start_logging_thread()
        
        # 리더기 사용 시 자동으로 카드 리더 시작
        if settings.리더기_사용:
            self.start_reader()
        
    def setup_ui(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        if settings.리더기_사용:
            # NFC 모드 UI
            title_label = ttk.Label(main_frame, text=f"{settings.기숙사_이름} 기숙사 출입 관리 (NFC)", 
                                   font=('Arial', 16, 'bold'))
            title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
            
            self.status_label = ttk.Label(main_frame, text="작동중", 
                                         font=('Arial', 12))
            self.status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
            
            self.current_status_frame = ttk.Frame(main_frame)
            self.current_status_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20))
            
            self.current_status_label = ttk.Label(self.current_status_frame, text="ID카드를 태깅해주세요", 
                                                 font=('Arial', 50, 'bold'))
            self.current_status_label.grid(row=0, column=0)
            
            log_frame = ttk.LabelFrame(main_frame, text="출입 기록", padding="10")
            log_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        else:
            # 수동 입력 모드 UI (main_ht.py와 동일)
            title_label = ttk.Label(main_frame, text=f"{settings.기숙사_이름} 기숙사 출입 관리 (HID/수동)", 
                                   font=('Arial', 16, 'bold'))
            title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
            
            self.status_label = ttk.Label(main_frame, text="대기 중...", 
                                         font=('Arial', 12))
            self.status_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
            
            self.current_status_frame = ttk.Frame(main_frame)
            self.current_status_frame.grid(row=2, column=0, columnspan=2, pady=(0, 20))
            
            self.current_status_label = ttk.Label(self.current_status_frame, text="ID카드를 입력하세요", 
                                                 font=('Arial', 50, 'bold'))
            self.current_status_label.grid(row=0, column=0)
            
            # 수동 입력 프레임
            input_frame = ttk.LabelFrame(main_frame, text="입력", padding="10")
            input_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
            
            ttk.Label(input_frame, text="카드 ID:").grid(row=0, column=0, sticky=tk.W)
            self.card_id_entry = ttk.Entry(input_frame, width=30, font=('Arial', 12))
            self.card_id_entry.grid(row=0, column=1, padx=(10, 0))
            self.card_id_entry.bind('<Return>', self.manual_check)
            self.card_id_entry.focus()
            
            ttk.Button(input_frame, text="확인", command=self.manual_check).grid(row=0, column=2, padx=(10, 0))
            
            log_frame = ttk.LabelFrame(main_frame, text="출입 기록", padding="10")
            log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, state='disabled')
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 그리드 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        if settings.리더기_사용:
            main_frame.rowconfigure(3, weight=1)
        else:
            main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def log_message(self, message, msg_type="info"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 메시지 타입에 따른 색상 설정
        colors = {
            "info": "black",
            "enter": "green",
            "exit": "red", 
            "warning": "orange",
            "error": "red"
        }
        
        color = colors.get(msg_type, "black")
        formatted_message = f"[{timestamp}] {message}\n"
        
        # 로그 텍스트를 일시적으로 활성화하여 내용 추가
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        
        # 색상 적용 (간단한 방법)
        if msg_type in ["enter", "exit", "warning", "error"]:
            self.log_text.tag_add(msg_type, f"end-2l", "end-1l")
            self.log_text.tag_config(msg_type, foreground=color)
        
        # 다시 비활성화
        self.log_text.config(state='disabled')
            
    def update_status_display(self, name, status):
        """큰 글씨로 출입 상태 표시"""
        if status == "출입":
            self.current_status_label.config(text=f"{name}님 출입", foreground="green")
        else:
            self.current_status_label.config(text=f"{name}님 외출", foreground="red")
    
    def task_started(self):
        """작업 시작 시 호출"""
        self.pending_tasks += 1
        self.current_processing = True
    
    def task_completed(self):
        """작업 완료 시 호출"""
        self.pending_tasks -= 1
        if self.pending_tasks <= 0:
            self.pending_tasks = 0
            self.current_processing = False
            # 스프레드시트와 로그시트 작업 완료 후 즉시 다음 카드 준비
            if settings.리더기_사용:
                self.current_status_label.config(
                    text="ID카드를 태깅해주세요", foreground="black")
            else:
                self.current_status_label.config(
                    text="ID카드를 입력하세요", foreground="black")
                # 입력창에 포커스
                if hasattr(self, 'card_id_entry'):
                    self.card_id_entry.focus()
            
    def manual_check(self, event=None):
        """수동 입력 확인 (리더기 사용하지 않을 때만)"""
        if not settings.리더기_사용 and hasattr(self, 'card_id_entry'):
            card_id = self.card_id_entry.get().strip()
            if card_id:
                self.log_message(f"💳 입력: {card_id}", "info")
                check_id(card_id, self)
                self.card_id_entry.delete(0, tk.END)
            
    def start_reader(self):
        """NFC 리더기 시작 (리더기 사용 시에만)"""
        if settings.리더기_사용 and not self.reader_active:
            self.reader_active = True
            self.reader_thread = threading.Thread(target=self.auto_read_cards, daemon=True)
            self.reader_thread.start()
            self.status_label.config(text="작동중")
            self.log_message("🔍 카드 리더가 시작되었습니다.", "info")
            
    def auto_read_cards(self):
        """NFC 카드 자동 읽기 (리더기 사용 시에만)"""
        if not settings.리더기_사용 or not NFC_AVAILABLE:
            return
            
        try:
            reader_list = readers()
            if not reader_list:
                self.log_message("❌ 리더를 찾을 수 없습니다. 연결 및 드라이버 확인 필요.", "error")
                return

            reader = reader_list[0]
            self.log_message(f"📖 사용 리더: {reader}", "info")
            self.log_message("💳 ID카드를 태깅해주세요", "info")

            while self.reader_active:
                try:
                    connection = reader.createConnection()
                    # 카드 올릴 때까지 대기
                    while self.reader_active:
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
                        self.log_message(f"🔍 감지된 UID: {uid}", "info")
                        check_id(uid, self)
                        importlib.reload(settings)
                    else:
                        self.log_message("⚠️ UID 읽기 실패 또는 카드 미인식", "warning")
                        threading.Thread(target=speak, args=('카드를 다시 대주세요', 1.7), daemon=True).start()

                    # 카드 뗄 때까지 대기
                    while self.reader_active:
                        try:
                            connection.transmit(GET_UID_APDU)
                            time.sleep(0.4)
                        except Exception:
                            break

                    connection.disconnect()
                    if self.reader_active:
                        self.log_message("💳 ID카드를 태깅해주세요", "info")
                    time.sleep(0.3)

                except Exception as e:
                    if self.reader_active:
                        self.log_message(f"❌ 리더 오류: {e}", "error")
                    time.sleep(0.5)
                    continue
                    
        except Exception as e:
            self.log_message(f"❌ 카드 리더 초기화 실패: {e}", "error")
            
    def start_logging_thread(self):
        if settings.로깅시트사용:
            threading.Thread(target=make_logs, daemon=True).start()
            dp('make_logs 스레드 생성 성공')

# =====================================================
# 메인 실행
# =====================================================
if __name__ == "__main__":
    print(Fore.YELLOW + '이 프로그램은 Alpha 버전입니다. 버그가 발생할수 있습니다.')
    
    # 리더기 사용 여부에 따른 안내
    if settings.리더기_사용:
        if NFC_AVAILABLE:
            print("NFC 리더기 모드로 실행됩니다.")
        else:
            print("NFC 리더기 라이브러리가 없어 수동 입력 모드로 전환됩니다.")
            settings.리더기_사용 = False
    else:
        print("수동 입력 모드로 실행됩니다.")
    
    root = tk.Tk()
    app = DormitoryApp(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("프로그램 종료됨.")
