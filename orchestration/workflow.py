"""
orchestration/workflow.py  —  CertifyMe sequential pipeline
Built with the Microsoft Agent Framework (agent-framework SDK).
Docs: learn.microsoft.com/en-us/agent-framework/workflows/orchestrations/sequential
"""

import asyncio
import json
import re

from agent_framework.orchestrations import SequentialBuilder
from agent_framework import WorkflowEvent
from mcp_tools.mslearn_mcp import search_mslearn

# Import our modular, pre-instantiated agents
from agents.syllabus_agent import syllabus_parser_agent
from agents.curator_agent import learning_path_curator_agent
from agents.planner_agent import study_plan_generator_agent
from agents.engagement_agent import engagement_coach_agent
from agents.assessment_agent import assessment_agent, recommendation_agent


# ── JSON extraction (strips markdown fences if the model adds them) ──────────

def _extract_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse agent JSON:\n{text[:400]}")


# ── Core runner: SequentialBuilder + run_stream ──────────────────────────────

def _run_pipeline(participants: list, message: str) -> list[dict]:
    """
    Builds a sequential Agent Framework pipeline and runs it.
    Each agent sees the full conversation history from prior agents.
    Returns the final conversation as a list of {role, content, author_name} dicts.
    """
    workflow = SequentialBuilder(participants=participants).build()

    async def _run():
        # Execute the workflow which resolves the full conversation array
        result = await workflow.run(message)
        
        # The result of SequentialBuilder.run() exposes .get_outputs()
        # which returns a list of outputs for each agent step.
        # We want the final outputs from the last agent.
        if hasattr(result, "get_outputs"):
            outputs = result.get_outputs()
            if outputs:
                return outputs[-1]  # Return the last agent's messages
            
        # Fallbacks for other SDK versions
        if hasattr(result, "messages"):
            return result.messages
        if isinstance(result, list):
            return result
        return getattr(result, "data", [])

    messages = asyncio.run(_run())
    return [
        {
            "role": getattr(m, "role", "assistant"),
            "content": getattr(m, "text", str(m)),
            "author_name": getattr(m, "author_name", None),
        }
        for m in messages
    ]


def _last_response(conv: list[dict], author: str = None) -> str:
    for m in reversed(conv):
        if m["role"] == "assistant" and (author is None or m.get("author_name") == author):
            return m["content"]
    return ""


def _single_agent(agent_obj, context: list[dict], task: str):
    """Run one agent with full prior conversation as context."""
    ctx_block = "\n".join(
        f"[{m.get('author_name') or m['role']}]: {m['content'][:600]}"
        for m in context if m.get("content")
    )
    prompt = (f"=== Prior Context ===\n{ctx_block}\n\n" if ctx_block else "") + f"=== Task ===\n{task}"
    
    # Pass the instantiated agent object to the pipeline
    conv = _run_pipeline([agent_obj], prompt)
    
    # We dynamically get the agent name backwards from the object itself
    # agent_obj.name contains the name
    name = agent_obj.name
    
    response = _last_response(conv, author=name)
    updated = list(context) + [
        {"role": "user", "content": task},
        {"role": "assistant", "content": response, "author_name": name},
    ]
    return response, updated


# ============================================================================
# Pipeline stages
# ============================================================================

def run_syllabus_agent(exam: str, goals: str, stream_callback=None):
    """Pre-processing: parse topics into a structured syllabus (internal step)."""
    raw, conv = _single_agent(
        agent_obj=syllabus_parser_agent,
        context=[],
        task=(
            f"Exam or topics: {exam}\n"
            f"Student goals: {goals}\n\n"
            "Extract and structure the exam domains and subtopics."
        ),
    )
    return _extract_json(raw), conv


def run_curator_agent(syllabus: dict, conversation: list[dict],
                      mcp_progress_callback=None, stream_callback=None):
    """Sub-workflow Agent 1: curate MS Learn paths using MCP search results."""
    mcp_results = []
    for domain in syllabus.get("domains", []):
        query = f"{syllabus.get('exam', '')} {domain['name']} Microsoft Learn"
        if mcp_progress_callback:
            mcp_progress_callback(f"Searching: {domain['name']}…")
        results = search_mslearn(query)
        mcp_results.append({"domain": domain["name"], "results": results[:3]})

    mcp_context = "MS Learn search results:\n" + "\n".join(
        f"\n{r['domain']}:\n" + "\n".join(
            f"  - [{m['title']}]({m['url']}) — {m.get('description','')}"
            for m in r["results"]
        )
        for r in mcp_results
    )

    raw, conv = _single_agent(
        agent_obj=learning_path_curator_agent,
        context=conversation,
        task=(
            f"Syllabus:\n{json.dumps(syllabus, indent=2)}\n\n"
            f"{mcp_context}\n\n"
            "Curate the best learning path for each domain."
        ),
    )
    return _extract_json(raw), conv


def run_planner_agent(learning_paths: dict, conversation: list[dict], stream_callback=None):
    """Sub-workflow Agent 2: convert curated paths into a week-by-week study plan."""
    raw, conv = _single_agent(
        agent_obj=study_plan_generator_agent,
        context=conversation,
        task=(
            f"Learning paths:\n{json.dumps(learning_paths, indent=2)}\n\n"
            "Generate a week-by-week study plan with daily tasks and milestones."
        ),
    )
    return _extract_json(raw), conv


def run_engagement_agent(study_plan: dict, conversation: list[dict], stream_callback=None):
    """Sub-workflow Agent 3: set up reminders, nudges, and accountability plan."""
    raw, conv = _single_agent(
        agent_obj=engagement_coach_agent,
        context=conversation,
        task=(
            f"Study plan:\n{json.dumps(study_plan, indent=2)}\n\n"
            "Create a personalised engagement and reminder strategy."
        ),
    )
    return _extract_json(raw), conv


def run_assessment_agent(conversation: list[dict], stream_callback=None):
    """Post-checkpoint: generate a 10-question MCQ assessment."""
    raw, conv = _single_agent(
        agent_obj=assessment_agent,
        context=conversation,
        task=(
            "The student confirmed they are ready. "
            "Generate a 10-question practice exam covering all domains discussed."
        ),
    )
    return _extract_json(raw), conv


def run_recommendation_agent(assessment: dict, student_answers: dict,
                              conversation: list[dict], stream_callback=None):
    """
    Conditional branch after assessment:
      PASS (≥70%) → suggest Microsoft certification + booking steps
      FAIL (<70%) → identify weak domains + recommend loop-back
    """
    questions = assessment.get("questions", [])
    correct, wrong_domains, review = 0, [], []

    for q in questions:
        qid = q["id"]
        ans = student_answers.get(str(qid), student_answers.get(qid, ""))
        ok = ans == q["correct_answer"]
        if ok:
            correct += 1
        else:
            wrong_domains.append(q["domain"])
        review.append({"id": qid, "domain": q["domain"],
                        "student_answer": ans, "correct_answer": q["correct_answer"],
                        "is_correct": ok})

    score = round((correct / len(questions)) * 100) if questions else 0
    verdict = "PASS" if score >= 70 else "FAIL"

    raw, _ = _single_agent(
        agent_obj=recommendation_agent,
        context=conversation,
        task=(
            f"Score: {correct}/{len(questions)} ({score}%) — {verdict}\n"
            f"Answer review:\n{json.dumps(review, indent=2)}\n\n"
            "Provide a personalised recommendation."
        ),
    )

    rec = _extract_json(raw)
    rec.update({"score_percent": score, "correct": correct,
                 "total": len(questions), "verdict": verdict,
                 "weak_domains": list(set(wrong_domains))})
    return rec
