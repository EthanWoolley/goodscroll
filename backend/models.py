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


class ContextOut(BaseModel):
    context: str
    project_title: str | None = None


class ContextUpdate(BaseModel):
    context: str


class WikipediaCardOut(BaseModel):
    id: str
    type: str = "wikipedia"
    title: str
    extract: str
    url: str
    source_term: str
    thumbnail_url: str | None = None


class FeedItemOut(BaseModel):
    """Unified feed item; source discriminates shape."""
    source: str  # "question" | "rss" | "wikipedia"
    id: str
    # question card
    project_id: str | None = None
    project_title: str | None = None
    type: str | None = None  # multiple_choice | open_ended
    question: str | None = None
    options: list[str] | None = None
    status: str | None = None
    round: int | None = None
    created_at: str | None = None
    # rss
    title: str | None = None
    summary: str | None = None
    url: str | None = None
    published_at: str | None = None
    feed_source: str | None = None  # feed title for rss
    image_url: str | None = None
    # wikipedia
    extract: str | None = None
    source_term: str | None = None
    thumbnail_url: str | None = None
