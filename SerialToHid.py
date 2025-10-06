# USE NFC READER (SERIAL) AS A HID READER

from smartcard.System import readers
from smartcard.util import toHexString
import pyautogui
import time
from colorama import Fore, Style, init

init(autoreset=True)

def read_and_type_uid():
    reader_list = readers()
    if not reader_list:
        print("리더기를 찾을 수 없습니다. 연결 확인 필요.")
        return

    reader = reader_list[0]
    print(Fore.MAGENTA + f"사용 리더: {reader}" + Style.RESET_ALL)
    print(Fore.CYAN + "ID카드를 태깅해주세요 (Ctrl+C로 종료)" + Style.RESET_ALL)

    while True:
        try:
            connection = reader.createConnection()
            # 카드가 올라올 때까지 대기
            while True:
                try:
                    connection.connect()
                    break
                except Exception:
                    time.sleep(0.3)
                    continue

            # UID 요청 APDU
            GET_UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = connection.transmit(GET_UID_APDU)

            if sw1 == 0x90 and sw2 == 0x00:
                uid = toHexString(data).replace(" ", "")
                print(Fore.GREEN + f"감지된 UID: {uid}" + Style.RESET_ALL)

                # ✅ 키보드로 UID 자동 입력
                pyautogui.typewrite(uid)
                pyautogui.press("enter")

            else:
                print(Fore.YELLOW + "UID 읽기 실패" + Style.RESET_ALL)

            # 카드가 제거될 때까지 대기
            while True:
                try:
                    connection.transmit(GET_UID_APDU)
                    time.sleep(0.3)
                except Exception:
                    break

            connection.disconnect()
            print(Fore.MAGENTA + "카드 제거됨 — 다음 카드 대기 중..." + Style.RESET_ALL)
            time.sleep(0.3)

        except KeyboardInterrupt:
            print("종료됨.")
            break
        except Exception:
            time.sleep(0.5)
            continue


if __name__ == "__main__":
    read_and_type_uid()
