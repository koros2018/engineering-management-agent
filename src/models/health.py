class ReviewIssue(BaseModel):
    rule_id: str = ""
    rule_name: str = ""
    severity: str = "建议"  # 严重/警告/建议
    layer: str = ""
    description: str = ""
    detail: str = ""
    spec_code: str = ""
    spec_section: str = ""
    suggestion: str = ""

class ReviewSummary(BaseModel):
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0
    suggest_count: int = 0
    confidence: float = 0.0
    drawing_type: dict = {}
    layer_count: int = 0
    rules_applied: int = 0

class ReviewOutput(BaseModel):
    success: bool = True
    file_name: str = ""
    drawing_type: str = ""
    summary: ReviewSummary = ReviewSummary()
    issues: List[ReviewIssue] = []
    passed_rules: List[dict] = []
    specs_linked: List[dict] = []

class DocumentItem(BaseModel):
    type: str = ""
    icon: str = ""
    content: str = ""
    summary: str = ""

class DocumentsOutput(BaseModel):
    success: bool = True
    file_name: str = ""
    drawing_type: str = ""
    documents: List[DocumentItem] = []
    generated_at: str = ""

class PipelineOutput(BaseModel):
    success: bool = True
    file_name: str = ""
    drawing_type: str = ""
    project_info: dict = {}
    material_specs: dict = {}
    review: dict = {}
    documents: dict = {}
    execution_time: float = 0.0

class AnalyticsEvent(BaseModel):
    user_id: str = ""
    event: str = ""
    metadata: dict = {}
    timestamp: str = ""

class PerformanceOutput(BaseModel):
    timestamp: str = ""
    system: dict = {}
    modules: dict = {}
    llm: dict = {}
    cache: dict = {}
    data: dict = {}

class FeedbackInput(BaseModel):
    type: str = "suggestion"  # bug/feature/suggestion/praise
    score: int = 5  # 1-5
    content: str = ""
    contact: str = ""

class FeedbackOutput(BaseModel):
    success: bool = True
    message: str = ""

class LLMHealthOutput(BaseModel):
    status: str = ""
    models: dict = {}
    supervisor: dict = {}
    timeout_stats: dict = {}

class MessageResponse(BaseModel):
    success: bool = True
    message: str = ""

class HealthResponse(BaseModel):
    status: str = "ok"
    timestamp: str = ""
