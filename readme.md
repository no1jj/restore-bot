# no.1_jj 디스코드 복구 봇

## 📖 소개
no.1_jj는 디스코드 서버를 위한 고급 인증 시스템을 제공하는 봇입니다. OAuth2를 통한 안전한 인증 프로세스와 사용자 관리 기능을 제공하여 서버 보안을 강화합니다.

## ✨ 주요 기능

### ✨ 서버 복구
- 유저 복구
- 카테고리 복구 (미구현)
- 채널 복구 (미구현)
- 권한 복구 (미구현)
- 오토모드 복구 (미구현)


### 🔐 안전한 인증 시스템
- 디스코드 OAuth2를 통한 안전한 사용자 인증
- 커스터마이징 가능한 인증 메시지 및 버튼 설정
- 성공적인 인증 시 자동 역할 부여

### 🛡️ 강력한 보안 기능
- 화이트리스트/블랙리스트 시스템으로 사용자 접근 제어
  - 사용자 ID, IP 주소, 이메일 기반 필터링
- VPN 사용 감지 및 차단 기능
- 캡차(hCaptcha) 통합으로 봇 계정 차단

### 📊 로깅 및 모니터링
- 서버별 맞춤 로그 채널 설정
- 인증 성공/실패에 대한 상세 로그
- 오너를 위한 종합적인 오너 로그 시스템

### 📱 사용자 정보 관리
- 사용자 기기, 브라우저 정보 수집 (설정에 따라 선택적)
- IP 로깅 기능 (설정에 따라 선택적)
- 이메일 로깅 기능 (설정에 따라 선택적)

## 🔧 설치 방법

### 요구 사항
- Node.js v14 이상
- Python 3.8 이상
- Discord.js v14 이상
- SQLite3

### 설치 단계
1. 저장소 클론하기
```bash
git clone https://github.com/no1jj/restore-bot
cd no1jj-bot
```

2. 필요한 패키지 설치
```bash
npm install  # 웹 서버 종속성 설치
pip install -r requirements.txt  # 봇 종속성 설치
```

3. 설정 파일 구성
```bash
cp config.example.json config.json
# config.json 파일을 적절히 수정하세요
```

4. 시행일 수정
```
no1jj/discordUI.py 245줄, view/privacy_policy.ejs 265줄에 시행일 수정 ex: 2025년 4월 2일
```

4. 봇 실행
```bash
python main.py
```

## ⚙️ 설정 방법

### config.json 설정
```json
{
  "botToken": "봇토큰",
  "clientId": "클라이언트ID",
  "clientSecret": "클라이언트시크릿",
  "ownerId": "오너 디스코드 ID",
  "domain": "https://yourdomain.com",
  "DBFolderPath": "./DB",
  "DBPath": "./db.db",
  "port": 3000,
  "ownerLogWebhook": "오너로그웹훅URL",
  "hCaptchaSiteKey": "hCaptcha사이트키",
  "hCaptchaSecretKey": "hCaptcha시크릿키",
  "vpnApiKey": "VPN확인API키"
}
```

### 설정 항목 상세 설명

#### 필수 항목
1. **botToken**
   - Discord Developer Portal에서 Bot 탭에서 생성한 봇의 토큰
   - 취득 방법: Discord Developer Portal → Applications → 앱 선택 → Bot → Reset Token

2. **clientId**
   - Discord 앱의 고유 식별자
   - 취득 방법: Discord Developer Portal → Applications → 앱 선택 → OAuth2 → Client ID

3. **clientSecret**
   - Discord 앱의 보안 비밀 키
   - 취득 방법: Discord Developer Portal → Applications → 앱 선택 → OAuth2 → Client Secret

4. **ownerId**
   - 봇 소유자의 Discord ID (관리자 전용 명령어 실행 권한)
   - 취득 방법: Discord 설정 → 고급 → 개발자 모드 활성화 → 본인 프로필 우클릭 → ID 복사

5. **domain**
   - 봇의 OAuth2 인증 프로세스에 사용될 도메인
   - 개발 환경: `"domain": "http://localhost:3000"`
   - 프로덕션 환경: `"domain": "https://yourdomain.com"`
   - 주의: 끝에 슬래시(/)를 포함하지 마세요

#### 데이터베이스 설정
6. **DBFolderPath**
   - 서버별 데이터베이스 파일이 저장될 폴더 경로
   - 예: `"./DB"` (상대 경로) 또는 절대 경로

7. **DBPath**
   - 메인 데이터베이스 파일 경로 (화이트/블랙리스트 등 저장)
   - 예: `"./db.db"` (DBFolderPath와 일관되게 설정)

8. **port**
   - 웹 서버가 실행될 포트 번호
   - 기본값: `3000` (80, 443 포트는 관리자 권한 필요)

#### 로깅 및 보안 설정
9. **ownerLogWebhook**
   - 봇 관련 중요 이벤트를 기록할 Discord 웹훅 URL
   - 취득 방법: Discord 채널 설정 → 연동 → 웹훅 생성 → 웹훅 URL 복사

10. **hCaptchaSiteKey** & **hCaptchaSecretKey**
    - 캡차 인증에 사용될 hCaptcha 키
    - 취득 방법: [hCaptcha](https://www.hcaptcha.com/) 가입 → 새 사이트 추가 → Keys 확인

11. **vpnApiKey**
    - VPN 사용 여부 확인을 위한 API 키
    - 취득 방법: [vpnapi.io](https://vpnapi.io/)에 가입 → API 키 발급
    - 기능: VPN, 프록시, TOR 노드, 프라이빗 릴레이 감지

### 디스코드 개발자 포털 설정
1. [Discord Developer Portal](https://discord.com/developers/applications)에서 새 애플리케이션 생성
2. Bot 탭에서 봇 생성 및 토큰 발급
3. OAuth2 탭에서 리다이렉트 URL 설정: `https://yourdomain.com/verify`
4. 필요한 스코프 선택: `identify`, `email`, `guilds`, `guilds.join`

## 🎮 사용 방법

### 봇 초대하기
1. 다음 URL을 통해 봇을 서버에 초대: `https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands`

### 기본 명령어
- `/등록` - 서버를 봇에 등록합니다
- `/설정` - 서버 설정을 변경합니다
- `/인증` - 인증 메시지를 생성합니다
- `/정보` - 서버 정보 및 설정을 확인합니다
- `/화이트리스트관리` - 화이트리스트 사용자 관리 [오너 전용]
- `/블랙리스트관리` - 블랙리스트 사용자 관리 [오너 전용]
- `/복구` - 서버 및 유저 복구를 시작합니다

### 서버 설정 옵션
- IP 기록 여부: 인증 시 사용자 IP 기록 설정
- 이메일 기록 여부: 인증 시 사용자 이메일 기록 설정
- 로그 채널 설정: 인증 로그가 기록될 채널 지정
- 인증 역할 설정: 인증 성공 시 부여할 역할 지정
- 캡차 사용 여부: hCaptcha를 통한 사용자 검증 활성화
- VPN 차단 여부: VPN 사용자의 인증 차단 설정

## 🔨 기술 스택
- **백엔드**: Python, Discord.py, Discord.js
- **웹 서버**: Node.js, Express
- **데이터베이스**: SQLite3
- **인증 시스템**: Discord OAuth2
- **보안**: hCaptcha, VPN 감지 API (vpnapi.io)
- **프론트엔드**: EJS, CSS, JavaScript

## 📜 개인정보처리방침
본 봇은 인증 과정에서 개인정보를 수집합니다. 자세한 내용은 웹사이트의 개인정보처리방침 페이지를 참조하세요.

## 🤝 기여하기
이슈 보고와 풀 리퀘스트를 환영합니다. 중요한 변경사항은 먼저 이슈를 열어 논의해주세요.

## 📄 라이선스
이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.

## 📞 문의
문의사항이 있으시면 Discord: no.1_jj 또는 Mail: no1jj@proton.me 을 통해 연락해주세요.

---

⭐ 이 프로젝트가 마음에 드셨다면 스타를 눌러주세요! ⭐
