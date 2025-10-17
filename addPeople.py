# 등록 시스템 (NFC / 수동 겸용, A열에 추가)

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import gspread
from google.oauth2.service_account import Credentials
import time
import threading
from datetime import datetime
import importlib
import settings

# NFC 리더기 import
if settings.리더기_사용:
    try:
        from smartcard.System import readers
        from smartcard.util import toHexString
        NFC_AVAILABLE = True
    except ImportError:
        print("⚠️ NFC 라이브러리 없음, 수동 모드로 전환합니다.")
        NFC_AVAILABLE = False
else:
    NFC_AVAILABLE = False

# -------------------------------------------------
# 구글 시트 연결
# -------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

try:
    creds = Credentials.from_service_account_file(settings.JSON파일_경로, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(settings.스프레드시트_키).sheet1
except Exception as e:
    sheet = None
    print("❌ 스프레드시트 연결 실패:", e)


# -------------------------------------------------
# 주요 함수
# -------------------------------------------------
def add_new_person(card_id, gui):
    """카드 ID를 입력받으면 이름 입력 후 A열 기준으로 시트에 추가"""
    if not sheet:
        gui.log_message("❌ 스프레드시트 연결 실패", "error")
        return

    try:
        all_data = sheet.get_all_values()
        for row in all_data:
            if len(row) >= 2 and row[1] == card_id:
                gui.log_message(f"⚠️ 이미 등록된 카드입니다: {row[0]}", "warning")
                return

        # 이름 입력
        name = simpledialog.askstring("이름 입력", "이 카드의 이름을 입력하세요:")
        if not name:
            gui.log_message("⏹ 등록 취소됨", "warning")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # A열 기준으로 다음 빈 행 찾아서 삽입
        next_row = len(all_data) + 1
        sheet.update(f"A{next_row}:D{next_row}", [[name, card_id, "출입", now]])

        gui.log_message(f"✅ 등록 완료: {name} ({card_id}) → A{next_row}", "success")

    except Exception as e:
        gui.log_message(f"❌ 오류: {e}", "error")


# -------------------------------------------------
# Tkinter GUI
# -------------------------------------------------
class RegisterApp:
    def __init__(self, root):
        self.root = root
        mode = "NFC" if settings.리더기_사용 else "수동 입력"
        self.root.title(f"기숙사 등록 시스템 ({mode})")
        self.root.geometry("700x500")

        self.reader_active = False
        self.reader_thread = None

        self.setup_ui()

        if settings.리더기_사용:
            self.start_reader()

    def setup_ui(self):
        frm = ttk.Frame(self.root, padding=20)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="기숙사 등록 시스템", font=("Arial", 18, "bold")).pack(pady=10)

        self.status_label = ttk.Label(frm, text="대기 중...", font=("Arial", 12))
        self.status_label.pack(pady=10)

        self.info_label = ttk.Label(frm,
                                    text="ID카드를 태깅하거나 수동으로 입력하세요.",
                                    font=("Arial", 20, "bold"))
        self.info_label.pack(pady=20)

        if not settings.리더기_사용:
            input_frame = ttk.Frame(frm)
            input_frame.pack(pady=10)
            ttk.Label(input_frame, text="카드 ID:").grid(row=0, column=0)
            self.card_entry = ttk.Entry(input_frame, width=25, font=("Arial", 12))
            self.card_entry.grid(row=0, column=1, padx=10)
            ttk.Button(input_frame, text="등록", command=self.manual_add).grid(row=0, column=2)
            self.card_entry.bind("<Return>", self.manual_add)

        self.log_box = tk.Text(frm, height=12, state="disabled")
        self.log_box.pack(fill="both", expand=True, pady=10)

    def log_message(self, msg, kind="info"):
        color = {"info": "black", "error": "red", "warning": "orange", "success": "green"}.get(kind, "black")
        self.log_box.config(state="normal")
        self.log_box.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n", kind)
        self.log_box.tag_config(kind, foreground=color)
        self.log_box.see(tk.END)
        self.log_box.config(state="disabled")

    def manual_add(self, event=None):
        card_id = self.card_entry.get().strip()
        if card_id:
            add_new_person(card_id, self)
            self.card_entry.delete(0, tk.END)

    def start_reader(self):
        if not NFC_AVAILABLE:
            self.log_message("❌ NFC 라이브러리 없음, 수동 모드로 전환됨", "error")
            return
        self.reader_active = True
        self.reader_thread = threading.Thread(target=self.read_cards, daemon=True)
        self.reader_thread.start()
        self.status_label.config(text="NFC 리더 작동 중")
        self.log_message("🔍 리더기 시작됨", "info")

    def read_cards(self):
        try:
            reader_list = readers()
            if not reader_list:
                self.log_message("❌ 리더기 미검출", "error")
                return
            reader = reader_list[0]
            self.log_message(f"📖 리더: {reader}", "info")

            while self.reader_active:
                connection = reader.createConnection()
                while True:
                    try:
                        connection.connect()
                        break
                    except:
                        time.sleep(0.3)

                GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
                data, sw1, sw2 = connection.transmit(GET_UID_APDU)
                if sw1 == 0x90 and sw2 == 0x00:
                    uid = toHexString(data).replace(" ", "")
                    self.log_message(f"💳 UID 감지: {uid}", "info")
                    add_new_person(uid, self)
                    importlib.reload(settings)
                else:
                    self.log_message("⚠️ UID 읽기 실패", "warning")

                connection.disconnect()
                time.sleep(0.3)
        except Exception as e:
            self.log_message(f"❌ NFC 오류: {e}", "error")


# -------------------------------------------------
# 실행
# -------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = RegisterApp(root)
    root.mainloop()
