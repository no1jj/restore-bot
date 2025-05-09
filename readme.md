# RestoreBot - 디스코드 서버 복구 및 인증 봇

<div align="center">
  <img src="https://cdn.discordapp.com/attachments/1285786391757848643/1367123430956072960/image.png?ex=68137069&is=68121ee9&hm=9b81c1e364d8b5309ff7171ee3133970d4578f6666d4a0deb9fc89f43980df1f&" alt="RestoreBot" width="2000">
  <br>
  <p><strong>디스코드 서버의 완벽한 보안과 복구를 위한 고급 인증 솔루션</strong></p>
  
  <p>
    <img src="https://img.shields.io/badge/version-V1.5-blue.svg" alt="Version">
    <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/node-%3E%3D14.0.0-brightgreen.svg" alt="Node">
    <img src="https://img.shields.io/badge/python-%3E%3D3.11-blue.svg" alt="Python">
  </p>
</div>

## 🚀 소개

RestoreBot은 디스코드 서버 관리자를 위한 종합적인 보안 및 복구 솔루션입니다. OAuth2 기반의 안전한 인증 시스템, 서버 복구 기능, 사용자 관리 도구를 제공하여 여러분의 디스코드 서버를 보호하고 유지합니다.

### 주요 특징
- **🔐 고급 인증 시스템**: 디스코드 OAuth2를 통한 안전한 인증 프로세스
- **🛡️ 강력한 보안 기능**: VPN 감지, 화이트리스트/블랙리스트, hCaptcha 통합
- **🔄 서버 복구 기능**: 유저 및 서버 구조 복구 기능
- **🔗 고유 링크 시스템**: 서버별 맞춤 URL로 인증 페이지 쉽게 공유
- **📊 상세한 로깅 시스템**: 모든 인증 활동에 대한 투명한 기록
- **⚙️ 손쉬운 관리**: 직관적인 웹 기반 대시보드 및 봇 명령어

## ✨ 상세 기능

### 🔄 서버 복구 시스템
- **유저 복구**: 삭제된 서버의 멤버들을 자동으로 초대하여 복구
- **카테고리 복구**: 서버 카테고리 구조 복구 
- **채널 복구**: 텍스트 및 음성 채널 복구 
- **권한 복구**: 역할 및 권한 설정 복구 

### 🔐 인증 시스템
- **안전한 OAuth2 인증**: 디스코드의 공식 인증 시스템을 통한 보안 강화
- **커스터마이징 가능한 UI**: 서버에 맞는 인증 메시지 및 버튼 설정
- **역할 자동 부여**: 인증 성공 시 지정된 역할 자동 부여

### 🔗 고유 링크 시스템 (NEW)
- **서버별 맞춤 URL**: 서버별 고유한 짧은 URL 생성 가능
- **링크 통계**: 방문 횟수, 생성일, 마지막 방문 날짜 등 상세 정보 제공
- **웹 패널 관리**: 웹 패널을 통한 손쉬운 링크 설정 및 관리
- **봇 명령어 지원**: 디스코드 봇 명령어로도 링크 설정 및 관리 가능

### 🛡️ 보안 기능
- **화이트리스트/블랙리스트**: 다양한 기준으로 사용자 접근 제어
  - **사용자 ID**: 특정 사용자 허용/차단
  - **IP 주소**: 특정 IP나 IP 범위 허용/차단
  - **이메일**: 특정 이메일 도메인 또는 주소 허용/차단
- **VPN 감지 및 차단**: VPN, 프록시, TOR 노드 사용자 감지 및 필터링
- **캡차 인증**: hCaptcha 통합으로 봇 계정 및 자동화된 접근 차단

### 📊 로깅 및 모니터링
- **서버별 로그 채널**: 각 서버마다 별도의 로그 채널 설정 가능
- **상세한 인증 로그**: 인증 성공/실패에 대한 자세한 정보 기록
  - **사용자 정보**: 사용자명, ID, 글로벌 이름
  - **기기 정보**: OS, 브라우저 유형
  - **네트워크 정보**: IP 주소, 지역, ISP (관리자 설정에 따라 선택적)
- **관리자 로그**: 봇 소유자를 위한 종합적인 로그 시스템

## 📷 스크린샷

<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="https://cdn.discordapp.com/attachments/1337624999380521035/1368480107030904832/image.png?ex=68185fea&is=68170e6a&hm=0f3a5eb0e46560f4efbb3cfc3648935c6d12c84b6a453d78762018a2aa502382&" width="400px" alt="대시보드">
        <br>
        <em>메인 대시보드</em>
      </td>
      <td align="center">
        <img src="https://cdn.discordapp.com/attachments/1337624999380521035/1368480531322376263/image.png?ex=6818604f&is=68170ecf&hm=e04a7a91a07e6bfe5f174572ab53ee1aa430c33eb304818ab5fff45a005f197d&" width="400px" alt="인증 페이지">
        <br>
        <em>인증 페이지</em>
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="https://cdn.discordapp.com/attachments/1337624999380521035/1368480531322376263/image.png" width="400px" alt="고유 링크 설정">
        <br>
        <em>고유 링크 설정</em>
      </td>
      <td align="center">
        <img src="https://cdn.discordapp.com/attachments/1337624999380521035/1368483851072045117/image.png?ex=68186367&is=681711e7&hm=4ca7f1ea4b0fc66ee409e4ea42557164c2e4796576ec9b5b40c70a6b9a81d15f&" width="400px" alt="백업 페이지">
        <br>
        <em>백업 화면</em>
      </td>
    </tr>
  </table>
</div>

## 🔧 설치 방법

### 요구 사항
- Node.js v14 이상
- Python 3.11 이상
- Discord.js v14 이상
- SQLite3

### 설치 단계
1. 릴리즈 다운로드
```bash
https://github.com/no1jj/restore-bot/releases/tag/V1.5.2
```

2. 필요한 패키지 설치
```bash
npm install  # 웹 서버 종속성 설치
```

3. 설정 파일 구성
```bash
config.json 파일을 적절히 수정하세요
```

4. 파일 수정
```
bot/no1jj/discordUI.py 248줄, web/view/privacy_policy.ejs 244줄에 시행일 수정 ex: 2025년 5월 1일
web/routes.index.js 수정
```

5. 봇 실행
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

### 디스코드 개발자 포털 설정
1. [Discord Developer Portal](https://discord.com/developers/applications)에서 새 애플리케이션 생성
2. Bot 탭에서 봇 생성 및 토큰 발급
3. OAuth2 탭에서 리다이렉트 URL 설정: `https://yourdomain.com/verify`
4. 필요한 스코프 선택: `identify`, `email`, `guilds`, `guilds.join`

## 🎮 사용 방법

### 봇 초대하기
다음 URL을 통해 봇을 서버에 초대하세요:
```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

### 주요 명령어
- `/등록` - 서버를 봇에 등록합니다
- `/설정` - 서버 설정을 변경합니다
- `/인증` - 인증 메시지를 생성합니다
- `/인원` - 인증된 인원을 확인합니다
- `/정보` - 서버 정보, 설정 및 고유 링크 정보를 확인합니다
- `/화이트리스트관리` - 화이트리스트 사용자 관리 [오너 전용]
- `/블랙리스트관리` - 블랙리스트 사용자 관리 [오너 전용]
- `/복구` - 서버 및 유저 복구를 시작합니다
- `/백업` - 서버를 백업합니다

## 💻 웹 패널 기능
- **서버 관리자 대시보드**: 웹 기반 설정 패널
- **고유 링크 관리**: 맞춤형 URL 설정 및 통계 확인
- **사용자 친화적 UI**: 직관적이고 현대적인 인터페이스
- **실시간 설정 변경**: 설정 변경 사항 즉시 적용
- **모바일 반응형 디자인**: 모든 기기에서 접근 가능

## 📋 업데이트 내역

### V1.5.2 (최신)
- 1.5 업데이트로 인해 발생한 **버그 수정**
  
### V1.5 
- **고유 링크 시스템** 추가: 서버별 맞춤 URL 설정 및 관리 기능
- 디스코드 봇 명령어로 고유 링크 설정 기능 추가
- 웹 인터페이스 UI 개선
- 버그 수정 및 성능 최적화

### V1.3.4
- VPN 감지 시스템 개선
- 웹 패널 보안 강화
- 디자인 업데이트 및 사용성 개선
- 버그 수정 및 안정성 향상

### V1.0
- 초기 릴리즈

## 🔨 기술 스택
- **백엔드**: Python, Discord.py, Discord.js
- **웹 서버**: Node.js, Express
- **데이터베이스**: SQLite3
- **인증 시스템**: Discord OAuth2
- **보안**: hCaptcha, VPN 감지 API (vpnapi.io)
- **프론트엔드**: EJS, CSS, JavaScript

## 📜 개인정보처리방침
본 봇은 인증 과정에서 개인정보를 수집합니다. 자세한 내용은 웹사이트의 개인정보처리방침 페이지를 참조하세요.

## 📞 지원 및 문의
- **Discord**: no.1_jj
- **이메일**: no1jj@proton.me
- **이슈 트래커**: GitHub 이슈를 통해 버그 리포트 및 기능 요청 가능

## 📄 라이선스
이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.

---

<div align="center">
  <p>⭐ 이 프로젝트가 마음에 드셨다면 스타를 눌러주세요! ⭐</p>
  <p>© 2025-<%= new Date().getFullYear() %> no.1_jj. All Rights Reserved.</p>
</div>
