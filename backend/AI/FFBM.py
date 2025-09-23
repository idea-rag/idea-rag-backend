import os
import openai
from dotenv import load_dotenv
import json

load_dotenv()

class FFBM:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_ai_feedback(self, study_data_payload: dict) -> str:
        prompt_message = f"""
        학생의 공부 상태 데이터가 주어집니다. 이 데이터를 바탕으로 학생을 격려하고 동기를 부여하는 따뜻한 메시지를 한국어로 작성해주세요.
        2번 줄바꿈은 사용하지 말고, 이모티콘도 자제해 주세요.
        학생을 위해 따뜻한 한마디를 건네주세요.
        자신을 지칭하는 말을 자제해주세요.
        학생의 의지를 돋구고, 자존심을 세워줄 피드백이 필요합니다.
        데이터는 JSON 형식입니다:
        {json.dumps(study_data_payload, indent=2, ensure_ascii=False)}
        """
        try:
            print("OpenAI API에 피드백을 요청합니다...")
            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": '''당신은 학생의 학습 데이터를 분석하고 격려해주는 친절한 스터디 코치입니다.'''},
                    {"role": "user", "content": prompt_message}
                ]
            )
            llm_message = response.choices[0].message.content
            return llm_message
        except Exception as e:
            print(f"API 요청 중 오류가 발생했습니다: {e}")
            return "AI 코치를 호출하는 중에 문제가 발생했어요. 잠시 후 다시 시도해주세요."


if __name__ == "__main__":
    ffbm_instance = FFBM()
    sample_study_data = {
              "schedule": {
                "2023-09-22": [
                  {
                    "name": "할 일 내용",
                    "importance": 3,
                    "isChecked": False,
                    "whatDay": "금요일"
                  },
                  {
                    "name": "다른 할 일",
                    "importance": 1,
                    "isChecked": True,
                    "whatDay": "금요일"
                  }
                ],
                "2023-09-23": [
                  {
                    "name": "주말 할 일",
                    "importance": 2,
                    "isChecked": False,
                    "whatDay": "토요일"
                  }
                ]
              }
    }


    ai_response = ffbm_instance.get_ai_feedback(sample_study_data)

    print(ai_response)