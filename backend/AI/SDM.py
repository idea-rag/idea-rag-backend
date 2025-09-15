import os
import openai
from dotenv import load_dotenv
import json
import pathlib
import time
import re

load_dotenv()


class SDM:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4.1-mini"

    def _retrieve_relevant_workbooks(self, student_workbooks: list, all_workbooks_data: list) -> list:
        relevant_data = []
        for s_workbook in student_workbooks:
            for db_entry in all_workbooks_data:
                if (db_entry.get('publish') == s_workbook.get('publish') and
                        db_entry.get('workbook') == s_workbook.get('workbook') and
                        db_entry.get('grade') == s_workbook.get('grade')):
                    relevant_data.append(db_entry)
                    break
        return relevant_data

    def get_ai_schedule(self, study_data_payload: dict) -> dict:
        try:
            # Get the directory where the current script is located
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate to the backend directory and then to dict.json
            dict_path = os.path.join(current_dir, '..', 'dict.json')
            dict_path = os.path.normpath(dict_path)  # Normalize the path

            with open(dict_path, 'r', encoding='utf-8') as f:
                all_workbooks_data = json.load(f)

            student_workbooks = study_data_payload.get("workbooks", [])
            if not student_workbooks:
                return {"error": "학생의 문제집 정보(workbooks)가 제공되지 않았습니다."}

            relevant_workbook_data = self._retrieve_relevant_workbooks(student_workbooks, all_workbooks_data)

            if not relevant_workbook_data:
                return {"error": "데이터베이스에서 학생의 문제집 정보를 찾을 수 없습니다. 학년, 출판사, 문제집 이름을 확인해주세요."}

            relevant_data_str = json.dumps(relevant_workbook_data, ensure_ascii=False, indent=2)
            student_data_str = json.dumps(study_data_payload, ensure_ascii=False, indent=2)

            prompt_message = f"""
            당신은 전문 학습 컨설턴트입니다. 학생의 데이터와 제공된 참고 문제집 데이터를 바탕으로, 구체적이고 실천 가능한 4주간의 주간 학습 계획표를 작성해주세요.

            [지시사항]
            1. 아래 [학생 데이터]와 [참고 문제집 데이터]를 정밀하게 분석하세요.
            2. [참고 문제집 데이터]에 있는 단원('work' 리스트)들을 4주 동안 균등하고 논리적으로 배분하여 학습 계획을 세워주세요.
            3. 각 계획 항목에는 과목, 출판사, 문제집 이름, 공부할 단원명('scope'), 중요도(1~5), 완료 여부('isFinished': false)가 포함되어야 합니다.
            4. 학생이 지치지 않도록 주말(day 6, day 7)에는 학습량을 줄이거나 복습, 휴식을 배치해주세요.
            5. 최종 결과는 반드시 아래 [출력 JSON 형식]에 맞춰 다른 설명 없이 JSON 객체만 반환해주세요.

            [학생 데이터]
            {student_data_str}

            [참고 문제집 데이터]
            {relevant_data_str}

            [출력 JSON 형식]
            {{
              "<타임스탬프>": {{
                "1": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "2": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "3": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "4.": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ]
              }}
            }}
            """

            print("[INFO] OpenAI API에 RAG 기반 스케줄 생성을 요청합니다...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 학생 데이터와 제공된 참고 자료를 바탕으로 최적의 학습 스케줄을 JSON 형식으로 생성하는 AI입니다."},
                    {"role": "user", "content": prompt_message}
                ],
                temperature=0.5,
                response_format={"type": "json_object"}
            )

            llm_message = response.choices[0].message.content
            return json.loads(llm_message)

        except openai.APIError as e:
            print(f"[ERROR] OpenAI API 오류가 발생했습니다: {e}")
            return {"error": f"API 오류: {e}"}
        except json.JSONDecodeError as e:
            print(f"[ERROR] AI 응답을 JSON으로 파싱하는 중 오류가 발생했습니다: {e}")
            print(f"원본 응답: {llm_message}")
            return {"error": "AI 응답을 처리하는 데 실패했습니다. 응답 형식이 올바르지 않습니다."}
        except Exception as e:
            print(f"[ERROR] 스케줄 생성 중 예기치 않은 오류가 발생했습니다: {e}")
            return {"error": f"알 수 없는 오류가 발생했습니다: {e}"}

    def modify_ai_schedule(self, original_schedule: dict, modification_request: dict) -> dict:
        original_schedule_str = json.dumps(original_schedule, indent=2, ensure_ascii=False)
        modification_request_str = json.dumps(modification_request, indent=2, ensure_ascii=False)

        prompt_message = f"""
        당신은 학생의 기존 학습 스케줄을 사용자의 새로운 요구사항에 맞게 수정하는 AI 학습 코치입니다.

        [기존 학습 스케줄]
        {original_schedule_str}

        [수정 요청 사항]
        {modification_request_str}

        [지시사항]
        1. [수정 요청 사항]을 [기존 학습 스케줄]에 자연스럽게 반영하여 전체 4주 계획을 재구성해주세요.
        2. 특정 과목의 변경, 추가 또는 삭제 요청을 정확히 이행하고, 나머지 공부 시간과의 균형을 맞춰주세요.
        3. 결과는 다른 설명 없이 수정된 '완전한 형태의 4주 계획표 JSON 객체'로만 제공해주세요.
        """
        try:
            print("\n[INFO] OpenAI API에 스케줄 수정을 요청합니다...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 기존 스케줄을 사용자의 요청에 맞게 유연하게 수정하고 완전한 JSON 결과물만 반환하는 AI입니다."},
                    {"role": "user", "content": prompt_message}
                ],
                response_format={"type": "json_object"}
            )
            modified_schedule_str = response.choices[0].message.content
            return json.loads(modified_schedule_str)
        except Exception as e:
            print(f"[ERROR] 스케줄 수정 중 API 요청 오류가 발생했습니다: {e}")
            return {"error": "스케줄을 수정하는 중 AI 코치에게 문제가 발생했어요. 잠시 후 다시 시도해주세요."}


if __name__ == "__main__":
    sdm_handler = SDM()

    sample_study_data = {
        "user_id": "student_rag_test_01",
        "grade": "middleschool-1",
        "workbooks": [
            {
                "grade": "middleschool-1",
                "publish": "미래엔 (MiraeN)",
                "workbook": "국어"
            },
            {
                "grade": "middleschool-1",
                "publish": "비상교육 (VISANG)",
                "workbook": "수학"
            }
        ],
        "goal": "4주 안에 국어와 수학의 주요 1학기 단원을 끝내고 싶어요."
    }

    initial_schedule = sdm_handler.get_ai_schedule(sample_study_data)

    print("\n--- 🤖 AI 코치가 RAG 기반으로 생성한 초기 스케줄 ---")
    print(json.dumps(initial_schedule, indent=2, ensure_ascii=False))
    print("------------------------------------------------")

    if "error" not in initial_schedule:
        user_modification_request = {
            "request_type": "UPDATE_SUBJECT",
            "week": "2",
            "day": "day3",
            "target_subject": "수학",
            "new_plan": {
                "subject": "수학",
                "publish": "비상교육 (VISANG)",
                "workbook": "수학",
                "scope": "II. 문자와 식 > 2. 일차방정식의 활용 복습",
                "importance": 5,
                "isFinished": False
            },
            "reason": "일차방정식 활용이 어려워서 한번 더 복습하고 싶어요."
        }

        modified_schedule = sdm_handler.modify_ai_schedule(initial_schedule, user_modification_request)

        print("\n--- ✍️ AI 코치가 수정한 최종 스케줄 ---")
        print(json.dumps(modified_schedule, indent=2, ensure_ascii=False))
        print("------------------------------------")