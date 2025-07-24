# Fycus Backend

형이야~

## 🔧 설치 및 실행 (개발용)

### 1. 의존성 설치
```bash
uv sync
```
*uv가 없음? https://docs.astral.sh/uv/getting-started/installation/  
ㄴ uv 쓰세요 uv기반으로 도커 짜둠  
라이브러리 관리 & 간단사용법 
- 설치: ``uv add 라이브러리이름``
- 삭제: ``uv remove 라이브러리이름``
- 프로젝트랑 의존성 동기화: ``uv sync`` (알아서 다 깔림, 하나씩 설치 X)

### 2. DB 필요할때 (MongoDB 서버 열기)
```bash
docker compose -f docker-compose-dev.yml up -d
```
DB 대시보드: http://localhost:8081  
DB 연결주소: ``mongodb://root:password@localhost:27017/``   
(설정값은 docker-compose-dev.yml 파일에서 바꾸세요)

### 2. 환경 변수 설정
`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
MONGODB_URI=mongodb://root:password@rag-mongodb:27017/
JWT_SECRET_KEY={!YOU_MUST_CHANGE_THIS_VALUE!}
나머지는 코드 안봣음
```
*도커로 배포할때 MONGODB_URI값은 건들지마세요 (알아서 연결됨)

### 3. 서버 실행
```bash
uv run backend/main.py
```

서버는 `http://localhost:8000`에서 실행됩니다.

## 서버에 배포

### 1.docker compose 실행
```bash
docker compose up -d
```

끝.



