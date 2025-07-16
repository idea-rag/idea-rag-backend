import os
import openai
from dotenv import load_dotenv
import json

# .env 파일에서 환경 변수를 로드하고 클라이언트를 초기화합니다.
# 백엔드 서버가 시작될 때 한 번만 실행되는 것이 효율적입니다.
load_dotenv()

class SDM:
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_ai_schedule(study_data_payload: dict) -> str:
        prompt_message = f"""
        학생의 공부 .
        데이터는 JSON 형식입니다:
        {json.dumps(study_data_payload, indent=2, ensure_ascii=False)}
        """

        try:
            print("OpenAI API에 피드백을 요청합니다...")

            # OpenAI API 호출
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[
                    {"role": "system", "content": "당신은 학생의 요청을 바탕으로 스케쥴을 작성해주는 역할입니다."},
                    {"role": "user", "content": prompt_message}
                ]
            )

            # LLM 응답 메시지 반환
            llm_message = response.choices[0].message.content
            return llm_message

        except Exception as e:
            print(f"API 요청 중 오류가 발생했습니다: {e}")
            return "AI 코치를 호출하는 중에 문제가 발생했어요. 잠시 후 다시 시도해주세요."

    def modify_ai_schedule(ai_feedback_payload: dict) -> str:
        prompt_message = f""


# --- 이 코드를 백엔드에서 사용하는 방법 (실행 예시) ---
if __name__ == "__main__":
    SDM = SDM()
    # 1. 실제 백엔드에서는 HTTP 요청의 body 등에서 이 데이터를 받게 됩니다.
    #    여기서는 테스트를 위해 샘플 데이터를 직접 생성합니다.
    sample_study_data = {}

    # 2. 백엔드 로직 내에서 get_ai_feedback 함수를 호출합니다.
    ai_response = SDM.get_ai_feedback(sample_study_data)

    # 3. 반환된 메시지를 클라이언트에게 보내거나 다른 처리를 합니다.
    print("\n--- AI 코치로부터 받은 최종 메시지 ---")
    print(ai_response)
    print("------------------------------------")