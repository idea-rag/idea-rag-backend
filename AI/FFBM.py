import os
import openai
from dotenv import load_dotenv
import json

# .env 파일에서 환경 변수를 로드하고 클라이언트를 초기화합니다.
# 백엔드 서버가 시작될 때 한 번만 실행되는 것이 효율적입니다.
load_dotenv()

class FFBM:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_ai_feedback(study_data_payload: dict) -> str:
        prompt_message = f"""
        학생의 공부 상태 데이터입니다. 이 데이터를 바탕으로 학생을 격려하고 동기를 부여하는 따뜻한 메시지를 한국어로 작성해주세요.
        데이터는 JSON 형식입니다:
        {json.dumps(study_data_payload, indent=2, ensure_ascii=False)}
        """

        try:
            print("OpenAI API에 피드백을 요청합니다...")

            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "당신은 학생의 학습 데이터를 분석하고 격려해주는 친절한 스터디 코치입니다."},
                    {"role": "user", "content": prompt_message}
                ]
            )

            # LLM 응답 메시지 반환
            llm_message = response.choices[0].message.content
            return llm_message

        except Exception as e:
            print(f"API 요청 중 오류가 발생했습니다: {e}")
            return "AI 코치를 호출하는 중에 문제가 발생했어요. 잠시 후 다시 시도해주세요."


# --- 이 코드를 백엔드에서 사용하는 방법 (실행 예시) ---
if __name__ == "__main__":
    FFBM = FFBM()
    # 1. 실제 백엔드에서는 HTTP 요청의 body 등에서 이 데이터를 받게 됩니다.
    #    여기서는 테스트를 위해 샘플 데이터를 직접 생성합니다.
    sample_study_data = {
        "date": "20250711",
        "startingTime": "14:00",
        "currentSubject": "자료구조",
        "measurements": [
            {"currentTime": 1720674060, "measuringTime": 60, "focusingTime": 50, "focusingStatus": "fullyFocusing",
             "focusingDepth": 85, "lastRestTime": "00:01"},
            {"currentTime": 1720674120, "measuringTime": 60, "focusingTime": 35, "focusingStatus": "focusing",
             "focusingDepth": 60, "lastRestTime": "00:02"},
            {"currentTime": 1720674180, "measuringTime": 60, "focusingTime": 15, "focusingStatus": "notFocusing",
             "focusingDepth": 30, "lastRestTime": "00:03"},
            {"currentTime": 1720674240, "measuringTime": 60, "focusingTime": 48, "focusingStatus": "fullyFocusing",
             "focusingDepth": 82, "lastRestTime": "00:04"},
            {"currentTime": 1720674300, "measuringTime": 60, "focusingTime": 55, "focusingStatus": "fullyFocusing",
             "focusingDepth": 91, "lastRestTime": "00:05"}
        ]
    }

    # 2. 백엔드 로직 내에서 get_ai_feedback 함수를 호출합니다.
    ai_response = FFBM.get_ai_feedback(sample_study_data)

    # 3. 반환된 메시지를 클라이언트에게 보내거나 다른 처리를 합니다.
    print("\n--- AI 코치로부터 받은 최종 메시지 ---")
    print(ai_response)
    print("------------------------------------")