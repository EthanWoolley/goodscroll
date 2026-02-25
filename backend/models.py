from pydantic import BaseModel


class ProjectCreate(BaseModel):
    title: str
    description: str
    project_type: str  # 'creating' or 'learning'
    end_goal: str | None = None
    deadline: str | None = None


class ProjectOut(BaseModel):
    id: str
    title: str
    description: str
    project_type: str
    end_goal: str | None
    deadline: str | None
    created_at: str


class CardOut(BaseModel):
    id: str
    project_id: str
    type: str
    question: str
    options: list[str] | None
    status: str
    round: int
    created_at: str


class AnswerIn(BaseModel):
    card_id: str
    answer: str


class AnswersSubmit(BaseModel):
    answers: list[AnswerIn]


class ProjectCreateResponse(BaseModel):
    project: ProjectOut
    cards: list[CardOut]


class NextRoundResponse(BaseModel):
    status: str  # 'continue' or 'complete'
    cards: list[CardOut] = []


class InterestsSubmit(BaseModel):
    interests: list[str]


class RssFeedAdd(BaseModel):
    url: str
