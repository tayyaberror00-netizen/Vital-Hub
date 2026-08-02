import base64
import json

from django.conf import settings


# ── LLM client helper — OpenRouter (provider-agnostic gateway) ───────────────
# We deliberately do NOT call Google's Gemini API directly anymore. Gemini's
# native SDK/auth (google-genai) hit an unresolved, Google-side rollout bug in
# mid-2026 where newly issued API keys ("AQ." prefix) are rejected outright
# with 401 UNAUTHENTICATED, regardless of correct code — see:
# https://discuss.ai.google.dev/t/aq-key-401-access-token-type-unsupported-fully-configured-key-still-rejected-project-gen-lang-client-0867379035/172852
#
# OpenRouter (https://openrouter.ai) sits in front of 300+ models from every
# major provider through ONE stable API key and ONE OpenAI-compatible
# interface. If a specific free model ever gets delisted or rate-limited,
# you only need to change LLM_MODEL / LLM_MODEL_FALLBACKS below — no code,
# no SDK, no auth changes required. That's the actual fix for the class of
# problem we just hit, not just a one-time patch.

# Primary model: free, vision-capable (needed for X-ray + report analyzer),
# large context. Fallbacks are tried automatically if the primary is
# unavailable/delisted/rate-limited. Update this list any time OpenRouter's
# free roster changes — check https://openrouter.ai/models?max_price=0
LLM_MODEL = getattr(settings, 'OPENROUTER_MODEL', 'google/gemma-4-31b-it:free')
LLM_MODEL_FALLBACKS = [
    'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free',
    'meta-llama/llama-3.3-70b-instruct:free',
]


def _llm_client():
    api_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured. Add it to your .env file.")
    from openai import OpenAI
    return OpenAI(base_url='https://openrouter.ai/api/v1', api_key=api_key)


def _chat_complete(messages, json_mode: bool = False, max_tokens: int = 1000,
                    temperature: float = 0.7) -> str:
    """Send a chat completion, trying the primary model then falling back
    through LLM_MODEL_FALLBACKS if the primary is unavailable/delisted."""
    client = _llm_client()
    last_error = None
    for model in [LLM_MODEL] + LLM_MODEL_FALLBACKS:
        try:
            kwargs = {
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature,
            }
            if json_mode:
                kwargs['response_format'] = {'type': 'json_object'}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            last_error = e
            continue
    raise last_error


def _image_data_url(image_bytes: bytes, content_type: str) -> str:
    b64 = base64.b64encode(image_bytes).decode('utf-8')
    return f"data:{content_type};base64,{b64}"


class QuotaExceededError(Exception):
    """Raised when a normal user hits their weekly usage cap for an AI feature."""
    def __init__(self, action_type, limit):
        self.action_type = action_type
        self.limit = limit
        super().__init__(f"Weekly limit of {limit} reached for {action_type}.")


class UsageQuotaService:
    """Enforces per-user weekly quotas on AI features. Admins are exempt
    entirely — usage is still logged for the admin activity dashboard, just
    never blocked."""

    # Rolling 7-day caps for normal ('user' role) accounts. Tune freely —
    # this is the single source of truth for every limit in the app.
    WEEKLY_LIMITS = {
        'nutrition_plan': 3,
        'xray_scan':       5,
        'report_scan':     5,
    }

    @staticmethod
    def check(user, action_type: str):
        """Call BEFORE running the actual AI generation. Raises
        QuotaExceededError if a normal user is already at/over their weekly
        limit. Does NOT log anything — call log_usage() only after the
        generation actually succeeds, so a failed AI call never burns quota."""
        if user.role == 'admin':
            return
        limit = UsageQuotaService.WEEKLY_LIMITS.get(action_type)
        if limit is None:
            return
        from django.utils import timezone
        from datetime import timedelta
        from .models import AIUsageLog
        window_start = timezone.now() - timedelta(days=7)
        count = AIUsageLog.objects.filter(
            user=user, action_type=action_type, created_at__gte=window_start,
        ).count()
        if count >= limit:
            raise QuotaExceededError(action_type, limit)

    @staticmethod
    def log_usage(user, action_type: str, detail: str = ''):
        """Call AFTER a successful generation (for both normal users and
        admins — admins are exempt from limits but still show up in the
        admin activity dashboard)."""
        from .models import AIUsageLog
        AIUsageLog.objects.create(user=user, action_type=action_type, detail=detail[:255])

    @staticmethod
    def remaining(user, action_type: str):
        """Returns None for admins (unlimited) or an int for normal users."""
        from django.utils import timezone
        from datetime import timedelta
        from .models import AIUsageLog

        if user.role == 'admin':
            return None
        limit = UsageQuotaService.WEEKLY_LIMITS.get(action_type, 0)
        window_start = timezone.now() - timedelta(days=7)
        used = AIUsageLog.objects.filter(
            user=user, action_type=action_type, created_at__gte=window_start,
        ).count()
        return max(0, limit - used)


def _extract_json(raw: str) -> dict:
    """Models sometimes wrap JSON in markdown fences, add stray text, or —
    on very large structured responses — get cut off mid-object if they run
    out of output tokens. Handle all three cases before giving up."""
    raw = raw.strip()
    if raw.startswith('```'):
        parts = raw.split('```')
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith('json'):
            raw = raw[4:]
        raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    import re
    match = re.search(r'\{[\s\S]*\}', raw)
    candidate = match.group(0) if match else raw
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    # Last resort: the response was likely truncated mid-structure (ran out of
    # output tokens). Close any unterminated string, then pad with whatever
    # closing brackets are needed to balance what was opened.
    repaired = candidate
    if repaired.count('"') % 2 == 1:
        repaired += '"'
    stack = []
    for ch in repaired:
        if ch in '{[':
            stack.append(ch)
        elif ch in '}]':
            if stack:
                stack.pop()
    for ch in reversed(stack):
        repaired += '}' if ch == '{' else ']'
    return json.loads(repaired)


# ── Nutrition constants ───────────────────────────────────────────────────────

ACTIVITY_MULTIPLIERS = {
    'sedentary':   1.2,
    'light':       1.375,
    'moderate':    1.55,
    'active':      1.725,
    'very_active': 1.9,
}

GOAL_CONFIG = {
    'loss': {
        'calorie_delta': -500,
        'protein_ratio': 0.40,
        'carb_ratio':    0.30,
        'fat_ratio':     0.30,
    },
    'gain': {
        'calorie_delta': +400,
        'protein_ratio': 0.30,
        'carb_ratio':    0.50,
        'fat_ratio':     0.20,
    },
    'perf': {
        'calorie_delta': +250,
        'protein_ratio': 0.25,
        'carb_ratio':    0.55,
        'fat_ratio':     0.20,
    },
    'focus': {
        'calorie_delta': 0,
        'protein_ratio': 0.25,
        'carb_ratio':    0.40,
        'fat_ratio':     0.35,
    },
    'maintain': {
        'calorie_delta': 0,
        'protein_ratio': 0.30,
        'carb_ratio':    0.40,
        'fat_ratio':     0.30,
    },
}

GOAL_LABELS = {
    'loss':     'fat loss / weight reduction',
    'gain':     'muscle hypertrophy / weight gain',
    'perf':     'peak athletic performance',
    'focus':    'cognitive focus and mental clarity',
    'maintain': 'weight maintenance',
}

FALLBACK_RECOMMENDATIONS = {
    'loss':     ("High-protein metabolic deficit strategy. Prioritise lean proteins (chicken, fish, "
                 "legumes) and fibrous vegetables to maintain satiety without excess calories. "
                 "Avoid liquid calories; aim for 7–9 hours sleep to regulate ghrelin and cortisol."),
    'gain':     ("Anabolic caloric surplus calibrated for hypertrophy. Front-load complex "
                 "carbohydrates (oats, sweet potato, rice) pre/post workout for glycogen storage. "
                 "Time protein intake within 90 minutes post-training for maximum muscle protein synthesis."),
    'perf':     ("Performance optimisation protocol active. Carbohydrate-load 2–3 hours before "
                 "training for peak glycogen availability. Use fast-digesting proteins (whey isolate) "
                 "immediately post-effort; replace electrolytes lost during sustained output."),
    'focus':    ("Cognitive nutrition protocol: prioritise omega-3 fatty acids (salmon, walnuts, chia) "
                 "to support neuronal membrane integrity and neurotransmitter synthesis. Avoid blood "
                 "sugar spikes — choose low-GI complex carbohydrates and avoid refined sugars."),
    'maintain': ("Homeostatic maintenance protocol. Balanced macro distribution ensures stable energy "
                 "levels and hormonal balance. Focus on micronutrient density — include diverse "
                 "colourful vegetables, whole grains, and adequate hydration throughout the day."),
}


class NutritionService:

    @staticmethod
    def calculate(age: int, weight: float, height: float, goal: str,
                  gender: str = 'male', activity: str = 'moderate') -> dict:
        # Mifflin-St Jeor BMR
        if gender == 'female':
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5

        multiplier     = ACTIVITY_MULTIPLIERS.get(activity, 1.55)
        tdee           = bmr * multiplier
        cfg            = GOAL_CONFIG.get(goal, GOAL_CONFIG['maintain'])
        target_cal     = round(tdee + cfg['calorie_delta'])

        protein_g = round((target_cal * cfg['protein_ratio']) / 4)
        carbs_g   = round((target_cal * cfg['carb_ratio'])    / 4)
        fat_g     = round((target_cal * cfg['fat_ratio'])     / 9)

        height_m   = height / 100
        bmi        = round(weight / (height_m ** 2), 1)
        bmi_status = (
            'Underweight' if bmi < 18.5 else
            'Healthy'     if bmi < 25   else
            'Overweight'  if bmi < 30   else
            'Obese'
        )

        recommendation = NutritionService._ai_recommendation(
            age, weight, height, goal, gender, activity,
            target_cal, protein_g, carbs_g, fat_g, bmi, bmi_status,
        )

        return {
            'calories':      target_cal,
            'protein':       protein_g,
            'carbs':         carbs_g,
            'fats':          fat_g,
            'bmi':           bmi,
            'bmi_status':    bmi_status,
            'bmr':           round(bmr),
            'tdee':          round(tdee),
            'water_ml':      round(weight * 35),
            'protein_ratio': cfg['protein_ratio'],
            'carb_ratio':    cfg['carb_ratio'],
            'fat_ratio':     cfg['fat_ratio'],
            'recommendation': recommendation,
        }

    @staticmethod
    def _ai_recommendation(age, weight, height, goal, gender, activity,
                           calories, protein, carbs, fat, bmi, bmi_status) -> str:
        try:
            prompt = (
                f"You are a certified sports nutritionist. Patient profile:\n"
                f"Age {age}, {gender}, {weight}kg, {height}cm, BMI {bmi} ({bmi_status}), "
                f"activity: {activity}, goal: {GOAL_LABELS.get(goal, goal)}.\n"
                f"Daily targets: {calories} kcal | Protein {protein}g | Carbs {carbs}g | Fat {fat}g.\n\n"
                f"Write a precise, evidence-based 3-sentence nutritional recommendation. Cover:\n"
                f"1. The single most important dietary priority for this goal.\n"
                f"2. A key food-timing or meal-composition tip.\n"
                f"3. One often-overlooked micronutrient or lifestyle factor for this goal.\n"
                f"Clinical tone. No generic advice. 70 words max."
            )
            text = _chat_complete(
                [{'role': 'user', 'content': prompt}],
                max_tokens=220, temperature=0.7,
            )
            return text.strip()
        except Exception:
            return FALLBACK_RECOMMENDATIONS.get(goal, FALLBACK_RECOMMENDATIONS['maintain'])


# ── X-Ray constants ───────────────────────────────────────────────────────────

XRAY_ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
XRAY_MAX_MB       = 10

XRAY_PROMPT = """You are a radiology AI assistant for an educational demo platform.

Analyse the uploaded image and respond ONLY with a valid JSON object — no markdown fences, no extra text.

Required format:
{
  "confidence": <integer 0-100, how confident you are in the analysis>,
  "image_quality": "<Poor|Fair|Good|Excellent>",
  "scan_type": "<Chest X-Ray|Bone X-Ray|CT Scan|MRI|Ultrasound|Other Medical Scan|Non-Medical Image>",
  "structures_visible": ["<anatomical structure>", ...],
  "density_assessment": "<Normal Range|Increased Density|Decreased Density|Heterogeneous|Unable to Assess>",
  "observation": "<2-3 sentences describing visible structures and any notable features in clinical language>",
  "disclaimer": "Educational demo only — not for clinical diagnosis."
}

Rules:
- If this is not a medical image, set confidence to 0, scan_type to "Non-Medical Image", and explain in observation.
- Be factual about what is actually visible; do not fabricate pathology.
- structures_visible should list real anatomical structures you can identify."""


class XrayService:

    @staticmethod
    def analyze(image_file) -> dict:
        if image_file.size > XRAY_MAX_MB * 1024 * 1024:
            raise ValueError(f"Image must be under {XRAY_MAX_MB} MB.")

        content_type = image_file.content_type or 'image/jpeg'
        if content_type not in XRAY_ALLOWED_MIME:
            content_type = 'image/jpeg'

        image_bytes = image_file.read()
        data_url = _image_data_url(image_bytes, content_type)

        text = _chat_complete([{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': XRAY_PROMPT},
                {'type': 'image_url', 'image_url': {'url': data_url}},
            ],
        }], json_mode=True, max_tokens=1200, temperature=0.4)
        return _extract_json(text)


# ── Consultation chat ──────────────────────────────────────────────────────────

CONSULTATION_SYSTEM_PROMPT = (
    "You are the Vital Hub AI Health Assistant, embedded in a live telehealth "
    "consultation on a healthcare e-commerce platform. Answer health questions "
    "helpfully and briefly (2-4 sentences), and where relevant recommend a "
    "specific Vital Hub product (BP monitor, glucometer, heating belt, knee "
    "massager, fitness band, smart ring, etc). Always add a one-line disclaimer "
    "that this is not a substitute for professional medical advice when giving "
    "clinical guidance. Keep tone warm and professional."
)


class ConsultationService:

    @staticmethod
    def chat(message: str, history: list) -> str:
        messages = [{'role': 'system', 'content': CONSULTATION_SYSTEM_PROMPT}]
        for turn in history[-10:]:
            role = 'assistant' if turn.get('role') in ('ai', 'model', 'assistant') else 'user'
            messages.append({'role': role, 'content': turn.get('content', '')})
        messages.append({'role': 'user', 'content': message})

        text = _chat_complete(messages, max_tokens=400, temperature=0.7)
        return text.strip()


# ── Nutrition weekly plan + grocery list ──────────────────────────────────────

class NutritionPlanService:

    # Real product catalog the AI must choose from — keeps the recommendation
    # grounded in products that actually exist, while letting the model decide
    # which one fits the patient, instead of a hardcoded keyword-matcher.
    PRODUCT_CATALOG = {
        'wrist-bp-monitor': 'Bluetooth Wrist BP Monitor — for hypertension/blood pressure tracking',
        'glucometer':       'Glucometer GL 44 — for diabetes/blood glucose monitoring',
        'smart-ring':       'TK9 Smart Ring — general wellness, sleep and heart-rate tracking',
        'fitness-band':     'LIGE Fitness Band — activity tracking, good for weight/fitness goals',
        'glass-scale':      'Glass Weighing Scale — for weight management goals',
        'calorie-counter':  'Calorie Counter — for calorie-deficit / fat-loss goals',
        'knee-massager':    'Portable Knee Massager — for joint/knee pain or physiotherapy needs',
        'heating-belt':     'Heating Belt for the Back — for back pain/muscular tension',
    }

    @staticmethod
    def generate_week_plan(profile: dict) -> dict:
        halal_note = (
            "CRITICAL: Every meal must be 100% Halal - no pork, no alcohol, no haram ingredients."
            if profile.get('halal') else ""
        )
        budget_note = (
            "CRITICAL BUDGET CONSTRAINT: This patient is cost-conscious. Every meal must use "
            "cheap, widely available, everyday staple ingredients (lentils, seasonal local "
            "vegetables, eggs, rice, chicken, yogurt, potatoes, bread, etc). AVOID expensive, "
            "imported, out-of-season, or premium/specialty items (e.g. salmon, avocado, quinoa, "
            "exotic berries, protein powders, almonds/cashews in bulk). Prefer ingredients that "
            "are reused across multiple meals to minimise total grocery spend, and favour "
            "bulk-buyable staples over single-use specialty items."
            if profile.get('budget') else ""
        )
        exclusions = profile.get('exclusions') or []
        excl_note = f"STRICT exclusions: {', '.join(exclusions)}." if exclusions else ""

        report_context = (profile.get('report_context') or '').strip()
        clinical_note = (
            f"REAL CLINICAL CONTEXT from a recent medical report analysis — treat this as "
            f"authoritative and factor it into the plan: {report_context}"
            if report_context else ""
        )

        catalog_lines = "\n".join(f"- {pid}: {desc}" for pid, desc in NutritionPlanService.PRODUCT_CATALOG.items())

        prompt = (
            "You are a clinical dietitian AI. Generate a nutrition plan:\n"
            f"Weight:{profile['weight']}kg|Height:{profile['height']}cm|Age:{profile['age']}|"
            f"Gender:{profile['gender']}|Goal:{profile['goal']}|Activity:{profile['activity']}|"
            f"Conditions:{','.join(profile.get('diseases', [])) or 'None'}|"
            f"Calories:{profile['calories']}|Location:{profile.get('location', 'Pakistan')}\n"
            f"{halal_note}\n{budget_note}\n{excl_note}\n{clinical_note}\n\n"
            "CRITICAL: Every day MUST have COMPLETELY DIFFERENT meals. No repeats.\n\n"
            "You must also recommend exactly ONE product from this catalog that best "
            f"fits this patient's condition and goal:\n{catalog_lines}\n\n"
            'Respond ONLY with valid JSON:\n'
            '{"assessment":"3-4 sentence summary","days":[{"day":"Monday","breakfast":"...",'
            '"breakfastDesc":"...","lunch":"...","lunchDesc":"...","dinner":"...","dinnerDesc":"...",'
            '"snack":"..."}, ...7 days],"exclusions":"a single markdown string with bullet points using - , NOT a JSON array","exercise":"a single markdown string describing the weekly protocol, NOT a JSON array",'
            '"suggestedProductId":"<one catalog key exactly as given above>",'
            '"productReason":"1 sentence explaining why this product fits this patient"}'
        )
        text = _chat_complete(
            [{'role': 'user', 'content': prompt}],
            json_mode=True, max_tokens=6000, temperature=0.8,
        )
        result = _extract_json(text)

        # Guard against the model returning an id outside our real catalog
        if result.get('suggestedProductId') not in NutritionPlanService.PRODUCT_CATALOG:
            result['suggestedProductId'] = 'smart-ring'
            result.setdefault('productReason', 'A good general wellness tracker for your goals.')

        return result

    @staticmethod
    def generate_grocery_list(week_plan: list, budget: bool = False) -> dict:
        budget_note = (
            "\nThe patient is on a budget-friendly plan. For each category, quantify "
            "conservatively (avoid over-buying), consolidate duplicate ingredients across "
            "days into one combined quantity, and where relevant append a short cost-saving "
            "tip in parentheses (e.g. 'buy loose, not packaged', 'in-season is cheaper')."
            if budget else ""
        )
        prompt = (
            "You are a helpful assistant. Review this 7-day meal plan and generate a consolidated, "
            "categorized grocery shopping list.\n"
            f"{budget_note}\n"
            'Return ONLY valid JSON in this exact format:\n'
            '{"categories": [{"name": "Produce", "items": ["4 Apples", "2 bunches Spinach"]}, '
            '{"name": "Proteins", "items": ["1kg Chicken breast"]}]}\n\n'
            f"Meal Plan: {json.dumps(week_plan)}"
        )
        text = _chat_complete(
            [{'role': 'user', 'content': prompt}],
            json_mode=True, max_tokens=2000, temperature=0.4,
        )
        return _extract_json(text)


# ── Report analyzer (image / PDF upload -> real multimodal analysis) ──────────

REPORT_PROMPT = """You are an advanced medical report summarizer integrated into a healthcare
e-commerce platform called Vital Hub.

Analyze the attached medical report (image or scanned document) and respond ONLY with valid JSON,
no markdown fences, no extra text, in this exact format:
{
  "summary": "Friendly, conversational, multi-paragraph summary of the core health findings. No jargon.",
  "maintenance": "Specific practical habits or metrics guidelines the user should watch/maintain.",
  "conditionTag": "one of: 'high_bp', 'diabetes', 'fever', 'general'",
  "severity": "low, medium, or high",
  "suggestNutritionAI": true
}
Be factual about what is actually written/visible in the report; do not fabricate findings."""

REPORT_MAX_MB = 10
REPORT_ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/webp', 'application/pdf'}


class ReportAnalyzerService:

    @staticmethod
    def analyze(uploaded_file) -> dict:
        if uploaded_file.size > REPORT_MAX_MB * 1024 * 1024:
            raise ValueError(f"File must be under {REPORT_MAX_MB} MB.")

        content_type = uploaded_file.content_type or 'application/octet-stream'
        if content_type not in REPORT_ALLOWED_MIME:
            raise ValueError("Only JPG, PNG, WEBP, or PDF reports are supported.")

        if content_type == 'application/pdf':
            raise ValueError(
                "PDF analysis isn't supported on the current free model — "
                "please upload the report as a JPG/PNG/WEBP image instead."
            )

        file_bytes = uploaded_file.read()
        data_url = _image_data_url(file_bytes, content_type)

        text = _chat_complete([{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': REPORT_PROMPT},
                {'type': 'image_url', 'image_url': {'url': data_url}},
            ],
        }], json_mode=True, max_tokens=1500, temperature=0.4)
        return _extract_json(text)
