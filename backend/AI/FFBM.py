import os
import openai
from dotenv import load_dotenv
import json


# .env 파일이 있다면 환경 변수를 로드합니다.
load_dotenv()

class FFBM:
    def __init__(self):
        # 환경 변수에서 API 키를 가져옵니다. 실제 환경에서는 load_dotenv()를 활성화하세요.
        # self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        # 아래는 예시용 키입니다. 실제 키로 교체해야 합니다.
        self.client = openai.OpenAI()

    def get_ai_feedback(self, study_data_payload: dict, focus_data_payload: dict = None) -> str:
        # AI에게 전달할 기본 프롬프트 메시지
        prompt_message = """
        학생의 공부 상태 데이터를 바탕으로 학생을 격려하고 동기를 부여하는 따뜻한 메시지를 한국어로 작성해주세요.
        반드시 다음 사항을 지켜주세요:
        1. 줄바꿈 문자(\\n)를 절대 사용하지 마세요. 문장은 마침표(.)로 끝내고 한 줄로 이어서 작성하세요.
        2. 이모티콘을 사용하지 마세요.
        3. "AI", "저", "제가"와 같이 자신을 지칭하는 말을 사용하지 마세요.
        4. 학생의 이름 대신 "학생" 또는 "여러분"과 같은 호칭을 사용하세요.
        5. 학생의 의지를 북돋우고, 자존감을 세워줄 수 있는 긍정적인 피드백을 주세요.
        6. 제공된 데이터를 자연스럽게 문장에 녹여서 설명해주세요.
        """

        # 학습 관련 정보를 프롬프트에 추가
        study_info = []
        if 'subject' in study_data_payload:
            study_info.append(f"과목: {study_data_payload['subject']}")
        if 'topic' in study_data_payload:
            study_info.append(f"주제: {study_data_payload['topic']}")
        if 'goal' in study_data_payload:
            study_info.append(f"목표: {study_data_payload['goal']}")

        if study_info:
            prompt_message += f" 학생의 학습 정보: {', '.join(study_info)}."

        # 집중도 데이터가 있는 경우, 분석하여 프롬프트에 추가
        if focus_data_payload:
            time_slots = focus_data_payload.get('timeSlots', {})
            total_measure_sec = 0
            total_focus_sec = 0

            time_analyses = []
            for time_range, data in time_slots.items():
                slot_measure = data.get('measureTime', 0)
                slot_focus = data.get('focusTime', 0)
                time_display = f"{time_range}시대"
                slot_rate = (slot_focus / slot_measure * 100) if slot_measure > 0 else 0
                time_analyses.append({
                    'time': time_display,
                    'measure': slot_measure,
                    'focus': slot_focus,
                    'rate': slot_rate
                })
                total_measure_sec += slot_measure
                total_focus_sec += slot_focus

            focus_rate = (total_focus_sec / total_measure_sec * 100) if total_measure_sec > 0 else 0

            # AI에게 전달할 데이터 요약 부분
            focus_data_summary = f"\n{focus_data_payload.get('whenDay')}의 집중도 데이터 분석 결과입니다."
            focus_data_summary += f" 총 학습 시간은 {total_measure_sec / 60:.1f}분이었고, 이 중 {total_focus_sec / 60:.1f}분 동안 집중했습니다."
            focus_data_summary += f" 전체 집중도는 {focus_rate:.1f}% 입니다."

            if time_analyses:
                focus_data_summary += " 시간대별 분석 결과:"
                time_descriptions = []
                for analysis in time_analyses:
                    measure_min = analysis['measure'] / 60
                    focus_min = analysis['focus'] / 60
                    time_descriptions.append(
                        f" {analysis['time']}에는 {measure_min:.1f}분 중 {focus_min:.1f}분 집중({analysis['rate']:.1f}%)"
                    )
                focus_data_summary += ", ".join(time_descriptions) + "."

            prompt_message += focus_data_summary

            # ★★★ 집중도 수치에 따라 AI에게 피드백 방향을 구체적으로 지시 ★★★
            if focus_rate >= 70:
                prompt_message += "\n지시사항: 전체 집중도가 매우 높습니다. 이 점을 특별히 강조하여 학생의 노력을 크게 칭찬하고, 앞으로의 가능성에 대해 긍정적으로 이야기해주세요."
            elif focus_rate >= 40:
                prompt_message += "\n지시사항: 준수한 집중도를 보였습니다. 잘한 점을 언급하며, 조금만 더 노력하면 더 높은 성과를 낼 수 있다는 자신감을 심어주는 방향으로 격려해주세요."
            else:
                prompt_message += "\n지시사항: 이번에는 집중이 다소 어려웠던 것 같습니다. 결과에 대해 질책하지 말고, 잠시 쉬어가도 괜찮다는 점을 알려주며 다시 도전할 수 있도록 따뜻하게 위로하고 격려해주세요."

        try:
            print("--------------------------------------")

            response = self.client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {
                        "role": "system",
                        "content": "당신은 학생의 학습 데이터를 분석하고 지시사항에 따라 격려해주는 따뜻한 스터디 코치입니다. 모든 응답은 한 줄의 완결된 문장으로 자연스럽게 이어지게 작성해주세요."
                    },
                    {
                        "role": "user",
                        "content": prompt_message
                    }
                ],
                temperature=0.7,
                max_tokens=550
            )
            llm_message = response.choices[0].message.content
            llm_message = ' '.join(llm_message.split()).strip()
            return llm_message
        except Exception as e:
            print(f"API 요청 중 오류가 발생했습니다: {e}")
            return "AI 코치를 호출하는 중에 문제가 발생했어요. 잠시 후 다시 시도해주세요."


if __name__ == "__main__":
    ffbm = FFBM()

    test_study_data = {
        "subject": "과학",
        "topic": "광합성",
        "goal": "광합성 원리 이해"
    }

    # 1. 집중도가 높은 경우 (83.3%)
    print("\n[Case 1: 집중도 높은 경우]")
    high_focus_data = {
        "whenDay": "오늘",
        "timeSlots": {
            "16": {"measureTime": 1800, "focusTime": 1500}  # 30분 중 25분
        }
    }
    feedback1 = ffbm.get_ai_feedback(test_study_data, high_focus_data)
    print("생성된 AI 피드백:", feedback1)

    # 2. 집중도가 낮은 경우 (33.3%)
    print("\n[Case 2: 집중도 낮은 경우]")
    low_focus_data = {
        "whenDay": "어제",
        "timeSlots": {
            "21": {"measureTime": 1800, "focusTime": 600}  # 30분 중 10분
        }
    }
    feedback2 = ffbm.get_ai_feedback(test_study_data, low_focus_data)
    print("생성된 AI 피드백:", feedback2)