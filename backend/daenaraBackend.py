import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from openai import OpenAI
import json


client = OpenAI(
    base_url="https://api.tokenfactory.nebius.com/v1/",
    api_key=os.environ.get("NEBIUS_API_KEY"),
)

#MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct-fast"
CHAT_INTERACTION_MODEL_NAME = "Qwen/Qwen3-30B-A3B-Instruct-2507"
CODE_GENERATION_MODEL_NAME = "Qwen/Qwen3-Coder-30B-A3B-Instruct"

app = FastAPI(title="DaenaraCVBackend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Prompts
# -----------------------------
def _build_create_cv_prompt(user_info: str) -> str:
    return (
        "ROLE:\n"
        "You are an expert CV designer and front-end developer.\n\n"
        "INPUTS:\n"
        "- You will receive ONE attachment named template_cv that represents the desired visual style.\n"
        "- You will also receive the candidate data as JSON.\n\n"
        "TASK:\n"
        "1) Create a SINGLE self-contained HTML document that includes embedded CSS.\n"
        "2) The HTML must represent the candidate info described by the provided JSON. In each key-value pair the key "
        "represents a question and the value the answer provided by the user. \n"
        "STYLE REQUIREMENT (very important):\n"
        "- The produced CV MUST look very professional and modern.\n"
        "HARD CONSTRAINTS (must be satisfied):\n"
        "A) TEXT OVERFLOW / LAYOUT SAFETY:\n"
        "- No text may overflow outside its container.\n"
        "- All containers that include text MUST be resilient to long words/URLs/emails.\n"
        "- You MUST include CSS rules that prevent overflow, including:\n"
        "  * box-sizing: border-box; on all elements\n"
        "  * overflow-wrap: anywhere; and/or word-break: break-word; on text containers\n"
        "  * max-width: 100%; on layout columns and text blocks\n"
        "  * optional: hyphens: auto; where appropriate\n"
        "- If you use multi-column layouts (grid/flex), ensure columns do not force text outside the page.\n\n"
        "B) ICON POLICY (strict):\n"
        "- Icons must be implemented ONLY with Bootstrap Icons.\n"
        "- You MUST include the Bootstrap Icons stylesheet reference in the HTML <head> as:\n"
        "  <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css\">\n"
        "- Do NOT use images, SVG icons, external icon packs, Font Awesome, inline SVG, or any other icon source.\n"
        "- Use <i class=\"bi bi-...\"> for icons.\n\n"
        "C) TIMELINE / VISUAL MARKERS SAFETY:\n"
        "- If you implement timelines, vertical lines, dots, or any chronological visual markers:\n"
        "  * They MUST NOT overlap, cover, or intersect any text.\n"
        "  * They MUST be placed in their own dedicated column or container.\n"
        "  * Use CSS layout (flex/grid) with explicit spacing, not absolute positioning over text.\n"
        "  * Ensure enough horizontal padding/margin so that text never touches or crosses timeline elements.\n\n"
        "D) PDF / PRINT READINESS (must be satisfied):\n"
        "- The HTML must be optimized for saving/printing to PDF.\n"
        "- When the user prints/saves to PDF, the output must contain ONLY the CV content.\n"
        "- Do NOT include any UI controls, buttons, file paths, debugging text, or extra information outside the CV.\n"
        "- Provide robust @media print CSS so that:\n"
        "  * The page uses A4 sizing and proper margins.\n"
        "  * Colors/backgrounds remain consistent when printing.\n"
        "  * No content is cut off or lost across pages.\n"
        "  * Sections do not break awkwardly; use page-break rules (break-inside: avoid) for blocks when helpful.\n"
        "  * Remove shadows and any non-essential screen-only decorations in print.\n"
        "- Ensure the CV container is the only printable region and fills the printable area correctly.\n\n"
        "OUTPUT REQUIREMENTS:\n"
        "- Return ONLY the final HTML (no markdown, no explanations).\n"
        "- Use semantic HTML (header, section, h1-h3, ul/li).\n"
        "- Professional modern layout, clean typography, good spacing.\n"
        "- Do NOT invent data. Use ONLY the information provided in the JSON. You MUST rewrite them in a professional and "
        " grammatically perfect way\n"
        "- Keep it ATS-friendly (avoid overly complex visuals).\n"
        "- Don't use hyperlinks since the CV is intended to be converted to PDF. If you have to report a link as user "
        "information just write it.\n"
        "- Remove any profile picture area.\n\n"
        "CANDIDATE JSON:\n"
        f"{user_info}\n\n"
        "OUTPUT:\n"
        "Return only the final HTML.\n"
    )

def _build_further_questions(user_info: str) -> str:
    return (
        "You are an assistant in CV creation. The user has been asked several question in order to obtain the relevant "
        "information to create their CV. Here is a JSON reporting as (key,value) pairs the questions and the corresponding "
        "user answers. \nIf you think the information provided is enogh just respond with ENOUGH, otherwise respond with "
        "a JSON containing as (key, value) pairs the furthers useful questions in the form NUMBER-QUESTION as '1': 'Do "
        "you have a GitHub profile?' \n"
        f"USER INFO: {user_info}\n"
    )

def _build_questions_making_prompt(profile: str) -> str:
    return (
        "You are an assistant in CV creation. Your goal is to establish a set of sufficient and necessary questions"
        "to make to the user in order to obtain the information (both personal and professional) needed to compile a "
        " professional CV. Make at least 20 different questions. Be sure that questions cover his email, location and "
        "phone number. Don't ask question about expected salary. You can ask more things simultaneously as long as the "
        " expected answer is not very long \n. It's important to ask the user about his educations and all of his "
        "previous and current professional experiences. \n"
        f"The user professional profile has been retrieved: {profile}. If the profile corresponds to a valid "
        "professional profile return ONLY a JSON in which each key-value entry is of the form NUMBER-QUESTION"
        "(example of a key-value pair: \"1\":\"What is your name?\"). \n"
        "If the profile does not corresponds to a valid professional profile return ONLY the string 'INVALID PROFILE'."
    )

def _build_update_user_info_prompt(current_info: str, question: str, answer: str) -> str:
    return (
        "Your role is to assist establish if the user answers in a meaningful way to the question they were asked."
        f"The user current info is represented by the following JSON where each key-value couple is of the form"
        f"question_asked-user_answer: \n{current_info}\n\n (eg. 'What is your full name?' : 'John Carrick')"
        f"The user is asked the question: {question} and he provided the following answer: {answer}.\n"
        f"Your goal is to establish if the user answer is a valid answer to the asked question. \n"
        "No question is mandatory, this means that if the user express his will to not answer the question or does not "
        "provide the requested information because he lacks of them the answer MUST BE CONSIDERED VALID. \n"
        "If the answer is valid update and return the JSON containing their data with the new couple question-answer, "
        " otherwise return the string INVALID ANSWER. \n"
    )


# -----------------------------
# Output cleaning helpers
# -----------------------------
def _clean_model_output(text: str) -> str:
    text = (text or "").strip()
    fence_match = re.match(
        r"^```(?:json|html|css)?\s*(.*?)\s*```$",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fence_match:
        return fence_match.group(1).strip()
    return text

def _clean_json_response(response: str) -> dict:
    response.replace("\n", "").replace("\\","")
    return json.loads(response)


# -----------------------------
# LLM calls function
# -----------------------------
def _llm_generate_text(system_prompt: str, user_message: str, MODEL_NAME: str) -> str:
    """
    Calls Nebius OpenAI-compatible chat.completions with Qwen3.
    Returns plain text content.
    """
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_message}
                    ],
                },
            ],
            # consigliati per output deterministico (HTML/JSON)
            temperature=0.0,
            top_p=0.8,
        )
    except Exception as e:
        # errori rete/auth/quota ecc.
        raise RuntimeError(f"LLM_CALL_FAILED: {str(e)}") from e

    # OpenAI-compatible shape: resp.choices[0].message.content
    try:
        content = resp.choices[0].message.content
    except Exception:
        raise RuntimeError("LLM_BAD_RESPONSE: missing choices/message/content")

    return _clean_model_output(content)


# -----------------------------
# Endpoints
# -----------------------------
@app.post("/create_further_questions")
async def create_further_questions(user_info: str):

    system_prompt = "You are a helpful assistant."
    user_prompt = _build_further_questions(user_info=user_info)

    try:
        html = _llm_generate_text(system_prompt, user_prompt)
        if not html:
            return JSONResponse(status_code=502, content={"error": "EMPTY_LLM_RESPONSE"})
        return HTMLResponse(status_code=200, content=html, media_type="text/html; charset=utf-8")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"INTERNAL ERROR: {str(e)}"})


@app.post("/create_cv")
async def create_cv(user_info: str):
    """
    Input: user_info as string (should be JSON string)
    Output: HTML (string)
    """
    system_prompt = "You are a helpful assistant."
    user_prompt = _build_create_cv_prompt(user_info=user_info)

    try:
        html = _llm_generate_text(system_prompt, user_prompt, MODEL_NAME=CODE_GENERATION_MODEL_NAME)
        if not html:
            return JSONResponse(status_code=502, content={"error": "EMPTY_LLM_RESPONSE"})
        return HTMLResponse(status_code=200, content=html, media_type="text/html; charset=utf-8")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"INTERNAL ERROR: {str(e)}"})


@app.post("/answer_question")
async def answer_question(current_info: str, question: str, answer: str):
    """
    Input: current_info (string JSON), question, answer
    Output: updated JSON (string) or INVALID ANSWER error
    """
    system_prompt = "You are a helpful assistant."
    user_prompt = _build_update_user_info_prompt(
        current_info=current_info,
        question=question,
        answer=answer,
    )

    try:
        out = _llm_generate_text(system_prompt, user_prompt, MODEL_NAME=CHAT_INTERACTION_MODEL_NAME)

        if "INVALID ANSWER" in out:
            return JSONResponse(status_code=400, content={"error": out})

        return JSONResponse(status_code=200, content=_clean_json_response(out))

    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"INTERNAL ERROR: {str(e)}"})


@app.post("/create_questions")
async def create_questions(profile: str):
    """
    Input: profile string
    Output: JSON questions or INVALID_PROFILE error
    """
    system_prompt = "You are a helpful assistant."
    user_prompt = _build_questions_making_prompt(profile=profile)

    try:
        out = _llm_generate_text(system_prompt, user_prompt, MODEL_NAME=CHAT_INTERACTION_MODEL_NAME)

        if "INVALID PROFILE" in out:
            return JSONResponse(status_code=400, content={"error": "INVALID_PROFILE"})

        return JSONResponse(status_code=200, content=(_clean_json_response(out)))

    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"INTERNAL ERROR: {str(e)}"})
