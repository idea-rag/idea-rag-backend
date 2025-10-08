import os
import openai
from dotenv import load_dotenv
import json
import pathlib
import time
import re
from datetime import datetime, timedelta

load_dotenv()


class SDM:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = openai.OpenAI(api_key=api_key)
        self.model = "gpt-4.1"

    def _retrieve_relevant_workbooks(self, student_workbooks: list, all_workbooks_data: list) -> list:
        relevant_data = []
        for s_workbook in student_workbooks:
            for db_entry in all_workbooks_data:
                if (db_entry.get('publish') == s_workbook.get('publish') and
                        db_entry.get('workbook') == s_workbook.get('workbook') and  # 'subjects' → 'workbook'으로 변경
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

            student_workbooks = study_data_payload.get("subjects", [])
            if not student_workbooks:
                return {"error": "학생의 문제집 정보(workbooks)가 제공되지 않았습니다."}

            relevant_workbook_data = self._retrieve_relevant_workbooks(student_workbooks, all_workbooks_data)

            if not relevant_workbook_data:
                return {"error": "데이터베이스에서 학생의 문제집 정보를 찾을 수 없습니다. 학년, 출판사, 문제집 이름을 확인해주세요."}

            relevant_data_str = json.dumps(relevant_workbook_data, ensure_ascii=False, indent=2)
            student_data_str = json.dumps(study_data_payload, ensure_ascii=False, indent=2)
            current_date = datetime.now().strftime("%Y-%m-%d")

            prompt_message = f"""
            당신은 전문 학습 컨설턴트입니다. 학생의 데이터와 제공된 참고 문제집 데이터를 바탕으로, 구체적이고 실천 가능한 제시된 주 만큼, 만일 제시되지 않았다면 4주간의 학습 계획표를 작성해주세요. 주의 수는 when으로 나타내집니다.

            [지시사항]
            1. 아래 [학생 데이터]와 [참고 문제집 데이터]를 정밀하게 분석하세요.
            2. [참고 문제집 데이터]에 있는 단원('work' 리스트)들을 균등하고 논리적으로 배분하여 학습 계획을 세워주세요.
            3. 각 계획 항목에는 과목, 출판사, 문제집 이름, 공부할 단원명('scope'), 중요도(1~3), 완료 여부('isFinished': false)가 포함되어야 합니다.
            4. 학생이 지치지 않도록 주말(day 6, day 7)에는 학습량을 줄이거나 복습, 휴식을 배치해주세요.
            5. 최종 결과는 반드시 아래 [출력 JSON 형식]에 맞춰 다른 설명 없이 JSON 객체만 반환해주세요.

            [학생 데이터]
            {student_data_str}

            [참고 문제집 데이터]
            {relevant_data_str}

            [출력 JSON 형식]
            {{
              "{current_date}": {{
                "1": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "2": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "3": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "4": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ]
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

    def modify_ai_schedule(self, student_data: dict, relevant_workbooks: list, existing_schedule: dict, feedback: str) -> dict:
        """
        기존 스케줄과 사용자 피드백을 바탕으로 새로운 스케줄을 생성합니다.

        Args:
            student_data: 학생 정보 (userID, grade 등)
            relevant_workbooks: 관련 문제집 데이터
            existing_schedule: 기존 스케줄 데이터
            feedback: 사용자 피드백 (수정 요청 사항)

        Returns:
            dict: 수정된 스케줄 또는 에러 메시지
        """
        try:
            # 입력 데이터 검증
            if not student_data:
                return {"error": "학생 데이터가 제공되지 않았습니다."}

            if not relevant_workbooks:
                return {"error": "관련 문제집 데이터가 제공되지 않았습니다."}

            if not existing_schedule:
                return {"error": "기존 스케줄이 제공되지 않았습니다."}

            # 데이터 문자열로 변환
            student_data_str = json.dumps(student_data, ensure_ascii=False, indent=2)
            workbooks_data_str = json.dumps(relevant_workbooks, ensure_ascii=False, indent=2)
            existing_schedule_str = json.dumps(existing_schedule, ensure_ascii=False, indent=2)
            current_date = datetime.now().strftime("%Y-%m-%d")

            prompt_message = f"""
            당신은 전문 학습 컨설턴트입니다. 학생의 기존 학습 스케줄을 사용자의 피드백에 맞게 수정하여 새로운 학습 계획표를 작성해주세요.

            [지시사항]
            1. [기존 스케줄]을 기반으로 [사용자 피드백]의 요청사항을 반영해주세요.
            2. [관련 문제집 데이터]의 단원('work' 리스트)을 활용하여 학습 계획을 조정해주세요.
            3. 피드백이 구체적이지 않다면 학생에게 더 도움이 되는 방향으로 스케줄을 개선해주세요.
            4. 각 계획 항목에는 과목, 출판사, 문제집 이름, 공부할 단원명('scope'), 중요도(1~3), 완료 여부('isFinished': false)가 포함되어야 합니다.
            5. 학습량의 균형을 맞추고, 주말에는 적절한 휴식이나 복습을 배치해주세요.
            6. 최종 결과는 반드시 아래 [출력 JSON 형식]에 맞춰 다른 설명 없이 JSON 객체만 반환해주세요.
            7. 현재 날짜를 반드시 반영해주세요.

            [학생 데이터]
            {student_data_str}

            [관련 문제집 데이터]
            {workbooks_data_str}

            [기존 스케줄]
            {existing_schedule_str}

            [사용자 피드백]
            {feedback}
            
            [오늘의 날짜]
            {current_date}

            [출력 JSON 형식]
            {{
              "{current_date}": {{
                "1": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "2": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "3": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ],
                "4": [ {{ "name": "<학생ID>", "weekplan": {{ "day1": [{{...}}], ... "day7": [{{...}}] }} }} ]
              }}
            }}
            """

            print("[INFO] OpenAI API에 스케줄 수정을 요청합니다...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 기존 스케줄을 사용자의 피드백에 맞게 유연하게 수정하고 완전한 JSON 결과물만 반환하는 AI 학습 컨설턴트입니다."},
                    {"role": "user", "content": prompt_message}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            modified_schedule_str = response.choices[0].message.content
            return json.loads(modified_schedule_str)

        except openai.APIError as e:
            print(f"[ERROR] OpenAI API 오류가 발생했습니다: {e}")
            return {"error": f"API 오류: {e}"}
        except json.JSONDecodeError as e:
            print(f"[ERROR] AI 응답을 JSON으로 파싱하는 중 오류가 발생했습니다: {e}")
            return {"error": "AI 응답을 처리하는 데 실패했습니다. 응답 형식이 올바르지 않습니다."}
        except Exception as e:
            print(f"[ERROR] 스케줄 수정 중 예기치 않은 오류가 발생했습니다: {e}")
            return {"error": f"알 수 없는 오류가 발생했습니다: {e}"}


if __name__ == "__main__":
    sdm_handler = SDM()

    # 샘플 데이터로 테스트
    sample_student_data = {
        "user_id": "testuser123",
        "grade": "middleschool-1",
        "subjects": [
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
        "goal": "이번 달에는 수학 '방정식' 단원과 국어 '소나기' 작품을 완벽하게 이해하고 싶어요."
    }

    # 초기 스케줄 생성
    initial_schedule = sdm_handler.get_ai_schedule(sample_student_data)
    print("\n--- 🤖 AI 코치가 생성한 초기 스케줄 ---")
    print(json.dumps(initial_schedule, indent=2, ensure_ascii=False))

    if "error" not in initial_schedule:
        # 샘플 문제집 데이터 (실제로는 dict.json에서 가져옴)
        sample_workbooks = [
            {
                "grade": "middleschool-1",
                "publish": "미래엔 (MiraeN)",
                "workbook": "국어",
                "work": [
                    "운수 좋은 날",
                    "나의 모국어는 침묵",
                    "소나기",
                    "마음을 여는 소통, 공감",
                    "우주 쓰레기, 해결 방법은 없을까",
                    "함께 지키는 저작권",
                    "동물원, 과연 필요한가"
                ]
            },
            {
                "grade": "middleschool-1",
                "publish": "비상교육 (VISANG)",
                "workbook": "수학",
                "work": [
                    "자연수의 성질",
                    "정수와 유리수",
                    "문자와 식",
                    "일차방정식",
                    "좌표평면과 그래프"
                ]
            }
        ]

        # 피드백을 통한 스케줄 수정
        user_feedback = "수학이 너무 어려워서 진도를 조금 늦추고 싶어요. 그리고 국어 '소나기' 부분을 더 집중적으로 공부하고 싶습니다."

        modified_schedule = sdm_handler.modify_ai_schedule(
            student_data=sample_student_data,
            relevant_workbooks=sample_workbooks,
            existing_schedule=initial_schedule,
            feedback=user_feedback
        )

        print("\n--- ✍️ 피드백을 반영한 수정된 스케줄 ---")
        print(json.dumps(modified_schedule, indent=2, ensure_ascii=False))