import os
import openai
from dotenv import load_dotenv
import json

# .env 파일에서 환경 변수를 로드합니다.
# 이 파일이 프로젝트 루트에 있고 OPENAI_API_KEY="your_key" 형식의 내용이 있어야 합니다.
load_dotenv()

class SDM:
    """
    AI를 이용해 학습 스케줄을 생성하고 수정하는 클래스
    """

    def __init__(self):
        # 환경 변수에서 API 키를 가져와 OpenAI 클라이언트를 초기화합니다.
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"  # 최신 모델을 사용하면 더 좋은 결과를 얻을 수 있습니다.

    def get_ai_schedule(self, study_data_payload: dict) -> str:
        """
        학생의 초기 학습 데이터를 바탕으로 AI 스케줄을 생성합니다.
        :param study_data_payload: 학생의 학습 관련 데이터 (JSON/dict)
        :return: AI가 생성한 스케줄 문자열
        """
        # AI에게 전달할 프롬프트를 구성합니다.
        prompt_message = """
        당신은 전문 학습 컨설턴트입니다. 아래 학생 데이터를 바탕으로, 구체적이고 실천 가능한 주간 학습 계획표를 작성해주세요. 
        각 요일별, 시간대별로 어떤 과목을 얼마나 공부해야 할지 명확하게 제시해주세요. 
        학생이 지치지 않도록 적절한 휴식 시간도 포함해주세요.
        
    {
      1720508580: { #현재 타임스탬프
        1: [
        {
            name : <학생 ID>,
            publish : <출판사>,
            workbook : <문제집 이름>,
            scope : <이전 스케쥴에 끝낸 단원부터 목표 단원까지 스케쥴을 짤때, 목표 단원명>,
        }, 
        importance : <1~5까지 현재 스케쥴이 가지는 중요도>, 
        isFinished : <bool 형으로 현재 스케쥴이 완료되었는지, 아닌지>,
        ],
        2: [
        {
            name : <학생 ID>,
            publish : <출판사>,
            workbook : <문제집 이름>,
            scope : <이전 스케쥴에 끝낸 단원부터 목표 단원까지 스케쥴을 짤때, 목표 단원명>,
        }, 
        importance : <1~5까지 현재 스케쥴이 가지는 중요도>, 
        isFinished : <bool 형으로 현재 스케쥴이 완료되었는지, 아닌지>,
        ],
      },
      ...
      1720508580: { #현재 타임스탬프
        1: [
        {
            name : <학생 ID>,
            publish : <출판사>,
            workbook : <문제집 이름>,
            scope : <이전 스케쥴에 끝낸 단원부터 목표 단원까지 스케쥴을 짤때, 목표 단원명>,
        }, 
        importance : <1~5까지 현재 스케쥴이 가지는 중요도>, 
        isFinished : <bool 형으로 현재 스케쥴이 완료되었는지, 아닌지>,
        ],
        2: [
        {
            name : <학생 ID>,
            publish : <출판사>,
            workbook : <문제집 이름>,
            scope : <이전 스케쥴에 끝낸 단원부터 목표 단원까지 스케쥴을 짤때, 목표 단원명>,
        }, 
        importance : <1~5까지 현재 스케쥴이 가지는 중요도>, 
        isFinished : <bool 형으로 현재 스케쥴이 완료되었는지, 아닌지>,
        ],
       },
      }
    };
    이 형식으로 답변을 제공해주시길 바랍니다.
        [학생 데이터]
        """ + json.dumps(study_data_payload, indent=2, ensure_ascii=False)

        try:
            print("[INFO] OpenAI API에 초기 스케줄 생성을 요청합니다...")

            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 학생의 데이터를 분석하여 최적의 학습 스케줄을 짜주는 AI 학습 코치입니다."},
                    {"role": "user", "content": prompt_message}
                ],
                temperature=0.7,  # 약간의 창의성을 부여
            )

            # LLM 응답 메시지 반환
            llm_message = response.choices[0].message.content
            return json.load(llm_message)

        except Exception as e:
            print(f"[ERROR] API 요청 중 오류가 발생했습니다: {e}")
            return "AI 코치를 호출하는 중에 문제가 발생했어요. 잠시 후 다시 시도해주세요."

    def modify_ai_schedule(self, original_schedule: str, modification_request: dict) -> str:
        """
        기존 스케줄을 사용자의 수정 요청에 따라 변경합니다.
        :param original_schedule: AI가 이전에 생성했던 원본 스케줄
        :param modification_request: 사용자의 스케줄 수정 요청 데이터 (JSON/dict)
        :return: AI가 수정한 새로운 스케줄 문자열
        """
        # AI에게 수정을 요청하는 프롬프트를 구성합니다.
        prompt_message = f"""
        당신은 학생의 기존 학습 스케줄을 사용자의 새로운 요구사항에 맞게 수정하는 AI 학습 코치입니다.

        아래는 학생의 [기존 학습 스케줄]입니다.
        ---
        {original_schedule}
        ---

        이제 아래 [수정 요청 사항]을 반영하여 전체 스케줄을 자연스럽게 재구성해주세요.
        특정 과목을 추가하거나 변경하고, 나머지 공부 시간과의 균형을 맞춰주세요.
        결과는 수정된 '완전한 형태의 주간 계획표'로만 제공해주세요.

        [수정 요청 사항]
        {json.dumps(modification_request, indent=2, ensure_ascii=False)}
        """

        try:
            print("\n[INFO] OpenAI API에 스케줄 수정을 요청합니다...")

            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 기존 스케줄을 사용자의 요청에 맞게 유연하게 수정하는 AI 스케줄러입니다."},
                    {"role": "user", "content": prompt_message}
                ]
            )

            # 수정된 스케줄 결과 반환
            modified_schedule = response.choices[0].message.content
            return modified_schedule

        except Exception as e:
            print(f"[ERROR] API 요청 중 오류가 발생했습니다: {e}")
            return "스케줄을 수정하는 중 AI 코치에게 문제가 발생했어요. 잠시 후 다시 시도해주세요."


# --- 이 코드를 백엔드에서 사용하는 방법 (실행 예시) ---
if __name__ == "__main__":
    # 1. SDM 클래스 인스턴스 생성
    sdm_handler = SDM()

    # 2. (시나리오 1) 새로운 학생의 초기 스케줄 생성 요청
    # 실제 백엔드에서는 HTTP 요청의 body 등에서 이 데이터를 받게 됩니다.
    sample_study_data = {
        "user_id": "student123",
        "grade": "고등학교 2학년",
        "study_preference": {
            "favorite_subject": ["수학", "과학"],
            "difficult_subject": ["영어"],
            "available_time": "평일 저녁 7시-11시, 주말 오후 2시-10시",
            "goal": "모든 과목 성적을 5% 향상시키고 싶어요."
        }
    }

    # 3. get_ai_schedule 함수를 호출하여 초기 스케줄 생성
    initial_schedule = sdm_handler.get_ai_schedule(sample_study_data)

    print("\n--- 🤖 AI 코치가 생성한 초기 스케줄 ---")
    print(initial_schedule)
    print("------------------------------------")

    # 4. (시나리오 2) 학생이 특정 과목 추가/변경을 요청
    # 이 데이터 역시 클라이언트로부터 HTTP 요청으로 받게 됩니다.
    user_modification_request = {
        "id": "student123",
        "subject": {
            "grade": "middleschool-2",
            "publish": "미래엔 (MiraeN)",
            "workbook": "사회",
            "workstart": "인권과 헌법",
            "workend": "인구 변화와 인구 문제",
            "workamount": "7"
        },
        "request_detail": "기존 사회 스케쥴을 이걸로 바꿔주세요."
    }

    # 5. modify_ai_schedule 함수를 호출하여 스케줄 수정
    #    이때, 이전에 생성된 'initial_schedule'을 함께 전달합니다.
    modified_schedule = sdm_handler.modify_ai_schedule(initial_schedule, user_modification_request)

    print("\n--- ✍️ AI 코치가 수정한 최종 스케줄 ---")
    print(modified_schedule)
    print("------------------------------------")