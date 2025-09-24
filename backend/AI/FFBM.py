import os
import openai
from dotenv import load_dotenv
import json

load_dotenv()

class FFBM:
    def __init__(self):
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_ai_feedback(self, study_data_payload: dict, focus_data_payload: dict = None) -> str:
        # Prepare the base prompt for study data
        prompt_message = """
        학생의 공부 상태 데이터가 주어집니다. 이 데이터를 바탕으로 학생을 격려하고 동기를 부여하는 따뜻한 메시지를 한국어로 작성해주세요.
        2번 줄바꿈은 사용하지 말고, 이모티콘도 자제해 주세요.
        학생을 위해 따뜻한 한마디를 건네주세요.
        자신을 지칭하는 말을 자제해주세요.
        학생의 의지를 돋구고, 자존심을 세워줄 피드백이 필요합니다.
        """

        # Add study data to prompt in a natural way
        prompt_message += f"\n\n님의 학습 데이터를 살펴보니 다음과 같습니다: {json.dumps(study_data_payload, ensure_ascii=False)}"
        
        # Add focus data to prompt if available
        if focus_data_payload:
            # Calculate focus rate
            total_measure = focus_data_payload.get('totalMeasureTime', 1)
            total_focus = focus_data_payload.get('totalFocusTime', 0)
            focus_rate = (total_focus / total_measure * 100) if total_measure > 0 else 0
            
            # Build focus data description
            focus_desc = f"\n\n{focus_data_payload.get('whenDay')}의 집중도 데이터를 확인해보니, "
            focus_desc += f"총 {total_measure}분 동안 공부하시는 동안 {total_focus}분 동안 집중하셨네요. "
            focus_desc += f"전체 집중도는 {focus_rate:.1f}%로, "
            
            # Add time slot analysis
            time_slots = focus_data_payload.get('timeSlots', {})
            if time_slots:
                focus_desc += "시간대별로는 "
                time_descriptions = []
                for time_range, data in time_slots.items():
                    slot_measure = data.get('measureTime', 0)
                    slot_focus = data.get('focusTime', 0)
                    slot_rate = (slot_focus / slot_measure * 100) if slot_measure > 0 else 0
                    time_descriptions.append(f"{time_range}시에는 {slot_rate:.1f}%")
                focus_desc += ", ".join(time_descriptions) + "의 집중도를 보였습니다. "
            
            # Add focus analysis
            if focus_rate >= 70:
                focus_desc += "매우 높은 집중력을 보이고 계시네요. 이렇게 꾸준히만 하시면 좋은 결과가 있을 거예요."
            elif focus_rate >= 40:
                focus_desc += "적절한 집중도를 보이고 계시네요. 조금만 더 집중력을 유지하시면 더 좋은 성과를 이끌어낼 수 있을 거예요."
            else:
                focus_desc += "오늘은 집중하기가 조금 어려우셨나 봐요. 잠시 휴식을 취하시고 다시 도전해보세요. "
                focus_desc += "집중력은 훈련을 통해 점점 좋아질 거예요."
            
            prompt_message += focus_desc
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