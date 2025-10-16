#region 기본설정
기숙사_이름 = '기숙사 이름을 넣어주세요'
스프레드시트_키 = '스프레드시트의 키를 입력해주세요'
JSON파일_경로 = 'service_account.json'
리더기_사용 = False #PC/SC 리더기 사용시 True
로딩중_전체표시 = True
로딩중_기숙사표시 = True
로딩중_기숙사_지연시간 = 0.3 # 초단위
로딩소요시간_표시 = True
카드체크후_메세지지우기 = False
디버그_모드 = False #디버그 모드. 웬만하면 일반 사용자는 사용 안해도 됌.
#endregion

#region 로깅시트
로깅시트사용 = True
로깅시트_이름 = '로깅시트의 이름을 적어주세요'
로깅시트_가로열 = '26' #기본값 : 26
로깅시트_세로열 = '30000' #기본값 : 30000
#endregion

"""%time : 현재 시간 (HH:MM:SS) / %date : 현재 날짜 (YYYY-MM-DD) / %name : 태깅한 이름 / %id : 태깅한 카드 번호"""
#region 음성출력
음성출력 = True
음성출력_배속 = 2 # 2배속이 기본
음성출력_언어 = 'ko' # 한국어 : ko / 영어 : en
음성출력_메세지_출입 = '%name 학생, 안녕하세요!'
음성출력_메세지_외출 = '%name 학생, 안녕히가세요!'
음성출력_없는정보 = '등록되지 않은 정보입니다.'
#endregion

#region 터미널출력
터미널출력_메세지_출입 = '%name 학생, 안녕하세요!'
터미널출력_메세지_외출 = '%name 학생, 안녕히가세요!'
터미널출력_없는정보 = '등록되지 않은 정보입니다.'
#endregion

#region 지챗전송
지챗전송 = True
지챗_웹훅_링크 = ['지챗 웹훅 링크들을 입력해주세요'] # 여러개 설정 가능
지챗_출입메세지 = '👋 %name 학생, 출입했습니다.\n⏰ %date %time'
지챗_외출메세지 = '👋 %name 학생, 외출했습니다.\n⏰ %date %time'
지챗_없는정보메세지 = '등록되지 않은 카드 사용 시도!\n(ID : %id)'
지챗_재전송시도 = True
지챗_재전송멈춤시간 = 1 # 초단위
지챗_재전송시도횟수 = 1
#endregion
try:
    import base64;exec(base64.b64decode("cHJpbnQoInNldHRpbmdzLnB564qUIOyEpOygleyaqSDtjIzsnbzsnoXri4jri6QhIOyLpO2Wie2VoCDtlYTsmpTqsIAg7JeG7Iq164uI64ukLiIpIGlmIF9fbmFtZV9fID09ICJfX21haW5fXyIgZWxzZSBwcmludChmIlwwMzNbMzRte19fbmFtZV9ffS5weSDroZzrlKnsmYTro4wiKQ=="))
except:
    pass
