# StudyRoomManagementServer
스터디룸 관리 서비스를 제공하는 서비스의 서버입니다.

# 기능
* 스터디룸 정보를 관리(추가, 삭제, 변경)합니다.
* 스터디룸 예약을 관리(추가, 삭제, 변경)합니다.
* 스터디룸 결제 정보를 관리(추가, 삭제)합니다.
* 단체 마일리지 정보를 관리합니다.


# 설치
1. `sudo apt install -y mariadb-server libmariadb-dev`
2. `pip3 install -r requirements.txt`

## 🚩 2.13.0을 만들며 느낀점
* 서비스를 운영하면서 다양한 장애사례에 관한 대처 방법을 경험하였습니다.
* Flask Framework에 대한 깊은 이해를 하였습니다.
* 초기 설계할 때 RESTful한 API를 설계하며 이해도가 깊어졌습니다.
* 문자 인증 서비스와 결제 서비스를 연동해보았습니다.

## ✨ 3.0.0을 만든다면 해보고 싶은 것
* 동기적인 코드를 비동기로 교체해보고 싶습니다.
* Swagger를 통한 Document 페이지를 자동화 하고싶습니다.
* MariaDB이외의 DB와도 연동해보고 싶습니다.
